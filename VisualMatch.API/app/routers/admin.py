import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models import Product
from app.routers.products_api import WITH_EMBEDDINGS, model_or_404, model_summaries, models_from, product_or_404, regenerate_product, translate_image_error
from app.services.backup_service import InvalidBackupError, create_backup, restore_backup
from app.services.embedding_service import ModelRegistry
from app.services.image_service import add_uploaded_images, delete_image_file, delete_product_directory, embedding_state, generate_all_pending_embeddings, generate_pending_embeddings

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory=str(config.BASE_DIR / "app" / "templates"))
templates.env.globals["embedding_state"] = embedding_state


def render_index(request: Request, db: Session, status_code: int = 200, **context):
    models = models_from(request)
    products = db.scalars(select(Product).options(WITH_EMBEDDINGS).order_by(Product.id)).all()
    # Per product: loaded models that still lack a current embedding for some of its images.
    incomplete = {
        product.id: [service.spec.name for service in models.available if any(embedding_state(image, service) != "current" for image in product.images)]
        for product in products
    }
    context = {"products": products, "incomplete": incomplete, "models": model_summaries(db, models), **context}
    return templates.TemplateResponse(request=request, name="products.html", context=context, status_code=status_code)


def generation_message(models: ModelRegistry, model_id: str, generated: int, failures: list[str]) -> str:
    message = f"{generated} embeddings de {models.get(model_id).spec.name} gerados"
    return f"{message}; {len(failures)} imagens falharam: {'; '.join(failures[:3])}" if failures else message


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    return render_index(request, db, success=request.query_params.get("success"))


@router.post("/admin/models/{model_id}/generate")
def generate_model_embeddings(request: Request, model_id: str, db: Session = Depends(get_db)):
    """Only the missing or outdated embeddings; current ones are kept."""
    model_or_404(models_from(request), model_id)
    try:
        generated, failures = generate_pending_embeddings(db, models_from(request), model_id)
    except Exception as exc:
        return render_index(request, db, status_code=422, error=translate_image_error(exc).detail)
    message = generation_message(models_from(request), model_id, generated, failures)
    if failures:
        return render_index(request, db, status_code=422, error=message)
    return RedirectResponse(f"/?success={message}", status_code=303)


@router.get("/admin/backup")
def download_backup(db: Session = Depends(get_db)):
    archive_path = create_backup(db)
    return FileResponse(archive_path, media_type="application/zip", filename="visualmatch-backup.zip", background=BackgroundTask(archive_path.unlink, missing_ok=True))


@router.post("/admin/restore")
async def upload_backup(request: Request, backup: UploadFile = File(...), db: Session = Depends(get_db)):
    if Path(backup.filename or "").suffix.lower() != ".zip":
        return render_restore_error(request, db, "Selecione um arquivo ZIP")
    handle = tempfile.NamedTemporaryFile(prefix="visualmatch-upload-", suffix=".zip", delete=False)
    temporary_path = Path(handle.name)
    try:
        while chunk := await backup.read(1024 * 1024):
            handle.write(chunk)
        handle.close()
        restore_backup(db, temporary_path)
        # The restored catalog may lack embeddings of some models.
        results = generate_all_pending_embeddings(db, models_from(request))
    except InvalidBackupError as exc:
        handle.close()
        return render_restore_error(request, db, str(exc))
    finally:
        handle.close()
        temporary_path.unlink(missing_ok=True)
        await backup.close()
    generated = sum(count for count, _ in results.values())
    failed = sum(len(failures) for _, failures in results.values())
    message = f"Backup restaurado com sucesso; {generated} embeddings gerados" + (f", {failed} imagens falharam" if failed else "")
    return RedirectResponse(f"/?success={message}", status_code=303)


def render_restore_error(request: Request, db: Session, message: str):
    return render_index(request, db, status_code=422, error=message)


@router.get("/admin/products/new", response_class=HTMLResponse)
def new_product(request: Request):
    return templates.TemplateResponse(request=request, name="product_form.html", context={"product": None})


@router.post("/admin/products/new")
async def create(request: Request, name: str = Form(...), images: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)):
    product = Product(name=name.strip())
    db.add(product); db.commit(); db.refresh(product)
    try:
        if images:
            await add_uploaded_images(db, product, images, models_from(request))
    except Exception as exc:
        db.delete(product); db.commit(); delete_product_directory(product.id)
        return templates.TemplateResponse(request=request, name="product_form.html", context={"product": None, "error": str(exc)}, status_code=422)
    return RedirectResponse(f"/admin/products/{product.id}", status_code=303)


@router.get("/admin/products/{product_id}", response_class=HTMLResponse)
def edit(request: Request, product_id: int, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="product_form.html", context={"product": product_or_404(db, product_id)})


@router.post("/admin/products/{product_id}")
async def save(request: Request, product_id: int, name: str = Form(...), images: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)):
    product = product_or_404(db, product_id)
    product.name = name.strip(); db.commit()
    try:
        if images:
            await add_uploaded_images(db, product, images, models_from(request))
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="product_form.html", context={"product": product_or_404(db, product_id), "error": str(exc)}, status_code=422)
    return RedirectResponse(f"/admin/products/{product_id}", status_code=303)


@router.post("/admin/products/{product_id}/images/{image_id}/delete")
def delete_image(product_id: int, image_id: int, db: Session = Depends(get_db)):
    product = product_or_404(db, product_id)
    image = next((item for item in product.images if item.id == image_id), None)
    if image:
        delete_image_file(image); db.delete(image); db.commit()
    return RedirectResponse(f"/admin/products/{product_id}", status_code=303)


@router.post("/admin/products/{product_id}/delete")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = product_or_404(db, product_id)
    db.delete(product); db.commit(); delete_product_directory(product_id)
    return RedirectResponse("/", status_code=303)


@router.post("/admin/products/{product_id}/regenerate")
def regenerate(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = product_or_404(db, product_id)
    try:
        regenerate_product(db, product, models_from(request))
        return RedirectResponse(f"/admin/products/{product_id}", status_code=303)
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="product_form.html", context={"product": product, "error": str(exc)}, status_code=422)
