from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import config
from app.database import get_db
from app.models import Product
from app.routers.products_api import product_or_404, regenerate_product, service_from
from app.services.image_service import add_uploaded_images, delete_image_file, delete_product_directory

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory=str(config.BASE_DIR / "app" / "templates"))


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    products = db.scalars(select(Product).options(selectinload(Product.images)).order_by(Product.id)).all()
    return templates.TemplateResponse(request=request, name="products.html", context={"products": products})


@router.get("/admin/products/new", response_class=HTMLResponse)
def new_product(request: Request):
    return templates.TemplateResponse(request=request, name="product_form.html", context={"product": None})


@router.post("/admin/products/new")
async def create(request: Request, name: str = Form(...), images: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)):
    product = Product(name=name.strip())
    db.add(product); db.commit(); db.refresh(product)
    try:
        if images:
            await add_uploaded_images(db, product, images, service_from(request))
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
            await add_uploaded_images(db, product, images, service_from(request))
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
        regenerate_product(db, product, service_from(request))
        return RedirectResponse(f"/admin/products/{product_id}", status_code=303)
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="product_form.html", context={"product": product, "error": str(exc)}, status_code=422)
