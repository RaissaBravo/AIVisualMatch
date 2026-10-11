from collections.abc import Iterable

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import config
from app.database import get_db
from app.models import ImageEmbedding, Product, ProductImage
from app.schemas import ProductDetail, ProductImageDetail, ProductListItem
from app.services.embedding_service import EmbeddingError, EmbeddingService, ModelRegistry, ModelUnavailableError, UnknownModelError
from app.services.image_service import InvalidImageError, add_uploaded_images, delete_image_file, delete_product_directory, embedding_from_json, is_current, store_embeddings

router = APIRouter(prefix="/api", tags=["products"])
WITH_EMBEDDINGS = selectinload(Product.images).selectinload(ProductImage.embeddings)


def models_from(request: Request) -> ModelRegistry:
    return request.app.state.models


def model_or_404(models: ModelRegistry, model_id: str | None) -> EmbeddingService:
    try:
        return models.get(model_id)
    except UnknownModelError as exc:
        raise HTTPException(status_code=404, detail=f"Modelo não registrado: {model_id}") from exc


def product_or_404(db: Session, product_id: int) -> Product:
    product = db.scalar(select(Product).options(WITH_EMBEDDINGS).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


def vector_for(image: ProductImage, service: EmbeddingService) -> list[float] | None:
    """Only vectors made by the ONNX file the app downloads; outdated ones would not compare."""
    record = image.embedding_for(service.spec.id)
    return embedding_from_json(record.embedding) if record and is_current(record.model_md5, service) else None


def vectors(images: Iterable[ProductImage], service: EmbeddingService) -> list[list[float]]:
    return [vector for image in images if (vector := vector_for(image, service)) is not None]


def detail(product: Product, models: ModelRegistry) -> ProductDetail:
    def embeddings(image: ProductImage) -> dict[str, list[float]]:
        return {model_id: vector for model_id, service in models.services.items() if (vector := vector_for(image, service)) is not None}

    return ProductDetail(
        id=product.id, name=product.name, created_at=product.created_at, updated_at=product.updated_at,
        images=[ProductImageDetail(id=i.id, file_name=i.file_name, url=f"/{i.file_path}", embeddings=embeddings(i), created_at=i.created_at) for i in product.images],
    )


def model_summaries(db: Session, models: ModelRegistry) -> list[dict]:
    """Model info plus how many catalog images have a current, outdated or no embedding for it."""
    rows = db.execute(select(ImageEmbedding.model_id, ImageEmbedding.model_md5, func.count()).group_by(ImageEmbedding.model_id, ImageEmbedding.model_md5)).tuples().all()
    total = db.scalar(select(func.count()).select_from(ProductImage)) or 0
    summaries = []
    for model_id, service in models.services.items():
        stored = [(md5, count) for row_model, md5, count in rows if row_model == model_id]
        current = sum(count for md5, count in stored if is_current(md5, service))
        outdated = sum(count for _, count in stored) - current
        summaries.append({
            **service.get_model_info(),
            "embedded_images": current, "outdated_images": outdated, "missing_images": total - current - outdated,
            "pending_images": total - current, "total_images": total,
        })
    return summaries


def translate_image_error(exc: Exception) -> HTTPException:
    if isinstance(exc, UnknownModelError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ModelUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (InvalidImageError, EmbeddingError)):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Erro interno ao processar imagens")


@router.get("/model-info")
def model_info(model: str | None = None, models: ModelRegistry = Depends(models_from)) -> dict:
    """Contract of ?model= (default: the first registered model)."""
    return model_or_404(models, model).get_model_info()


@router.get("/models")
def list_models(db: Session = Depends(get_db), models: ModelRegistry = Depends(models_from)) -> list[dict]:
    """Every registered model with its contract and coverage; the app builds its model picker from it."""
    return model_summaries(db, models)


@router.get("/models/{model_id}/file")
def download_model(model_id: str, models: ModelRegistry = Depends(models_from)) -> FileResponse:
    service = model_or_404(models, model_id)
    if not service.available:
        raise HTTPException(status_code=404, detail=service.load_error or "Modelo ONNX indisponível")
    return FileResponse(service.model_path, media_type="application/octet-stream", filename=service.model_path.name)


@router.get("/products", response_model=list[ProductListItem])
def list_products(model: str | None = None, db: Session = Depends(get_db), models: ModelRegistry = Depends(models_from)) -> list[ProductListItem]:
    """Embeddings of one model only (default: the first registered), never mixed."""
    service = model_or_404(models, model)
    products = db.scalars(select(Product).options(WITH_EMBEDDINGS).order_by(Product.id)).all()
    return [ProductListItem(id=p.id, name=p.name, embeddings=vectors(p.images, service)) for p in products]


@router.get("/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, request: Request, db: Session = Depends(get_db)) -> ProductDetail:
    return detail(product_or_404(db, product_id), models_from(request))


@router.post("/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
async def create_product(request: Request, name: str = Form(..., min_length=1, max_length=200), images: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)) -> ProductDetail:
    product = Product(name=name.strip())
    if not product.name:
        raise HTTPException(422, "Nome do produto é obrigatório")
    db.add(product)
    db.commit()
    db.refresh(product)
    try:
        if images:
            await add_uploaded_images(db, product, images, models_from(request))
    except Exception as exc:
        db.delete(product)
        db.commit()
        delete_product_directory(product.id)
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product.id), models_from(request))


@router.put("/products/{product_id}", response_model=ProductDetail)
async def update_product(product_id: int, request: Request, name: str = Form(..., min_length=1, max_length=200), images: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)) -> ProductDetail:
    product = product_or_404(db, product_id)
    if not name.strip():
        raise HTTPException(422, "Nome do produto é obrigatório")
    old_name = product.name
    product.name = name.strip()
    db.commit()
    try:
        if images:
            await add_uploaded_images(db, product, images, models_from(request))
    except Exception as exc:
        product.name = old_name
        db.commit()
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product_id), models_from(request))


@router.post("/products/{product_id}/images", response_model=ProductDetail)
async def upload_images(product_id: int, request: Request, images: list[UploadFile] = File(...), db: Session = Depends(get_db)) -> ProductDetail:
    product = product_or_404(db, product_id)
    if not images:
        raise HTTPException(422, "Envie ao menos uma imagem")
    try:
        await add_uploaded_images(db, product, images, models_from(request))
    except Exception as exc:
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product_id), models_from(request))


@router.delete("/products/{product_id}/images/{image_id}", status_code=204)
def remove_image(product_id: int, image_id: int, db: Session = Depends(get_db)) -> None:
    product_or_404(db, product_id)
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id))
    if image is None:
        raise HTTPException(404, "Imagem não encontrada")
    delete_image_file(image)
    db.delete(image)
    db.commit()


@router.delete("/products/{product_id}", status_code=204)
def remove_product(product_id: int, db: Session = Depends(get_db)) -> None:
    product = product_or_404(db, product_id)
    db.delete(product)
    db.commit()
    delete_product_directory(product_id)


def regenerate_images(db: Session, images: Iterable[ProductImage], models: ModelRegistry, model_id: str | None = None) -> int:
    """Re-embeds the images with one model, or with every loaded model; all-or-nothing."""
    count = 0
    try:
        for image in images:
            store_embeddings(image, models.generate_embeddings(config.BASE_DIR / image.file_path, model_id), models)
            count += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return count


def regenerate_product(db: Session, product: Product, models: ModelRegistry, model_id: str | None = None) -> None:
    regenerate_images(db, product.images, models, model_id)


@router.post("/products/{product_id}/regenerate-embeddings", response_model=ProductDetail)
def regenerate_embeddings(product_id: int, request: Request, model: str | None = None, db: Session = Depends(get_db)) -> ProductDetail:
    product = product_or_404(db, product_id)
    try:
        regenerate_product(db, product, models_from(request), model)
    except Exception as exc:
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product_id), models_from(request))


@router.post("/regenerate-all-embeddings")
def regenerate_all(request: Request, model: str | None = None, db: Session = Depends(get_db)) -> dict[str, int]:
    """Without ?model= refreshes every loaded model; with it, backfills just that one."""
    products = db.scalars(select(Product).options(WITH_EMBEDDINGS)).all()
    try:
        embedded = regenerate_images(db, [image for product in products for image in product.images], models_from(request), model)
    except Exception as exc:
        raise translate_image_error(exc) from exc
    return {"products": len(products), "embeddings": embedded}
