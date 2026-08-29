from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import config
from app.database import get_db
from app.models import Product, ProductImage
from app.schemas import ProductDetail, ProductImageDetail, ProductListItem
from app.services.embedding_service import EmbeddingError, EmbeddingService, ModelUnavailableError
from app.services.image_service import InvalidImageError, add_uploaded_images, delete_image_file, delete_product_directory, embedding_from_json, embedding_to_json

router = APIRouter(prefix="/api", tags=["products"])


def service_from(request: Request) -> EmbeddingService:
    return request.app.state.embedding_service


def product_or_404(db: Session, product_id: int) -> Product:
    product = db.scalar(select(Product).options(selectinload(Product.images)).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


def detail(product: Product) -> ProductDetail:
    return ProductDetail(
        id=product.id, name=product.name, created_at=product.created_at, updated_at=product.updated_at,
        images=[ProductImageDetail(id=i.id, file_name=i.file_name, url=f"/{i.file_path}", embedding=embedding_from_json(i.embedding), created_at=i.created_at) for i in product.images],
    )


def translate_image_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ModelUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (InvalidImageError, EmbeddingError)):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Erro interno ao processar imagens")


@router.get("/model-info")
def model_info(service: EmbeddingService = Depends(service_from)) -> dict:
    return service.get_model_info()


@router.get("/products", response_model=list[ProductListItem])
def list_products(db: Session = Depends(get_db)) -> list[ProductListItem]:
    products = db.scalars(select(Product).options(selectinload(Product.images)).order_by(Product.id)).all()
    return [ProductListItem(id=p.id, name=p.name, embeddings=[embedding_from_json(i.embedding) for i in p.images]) for p in products]


@router.get("/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductDetail:
    return detail(product_or_404(db, product_id))


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
            await add_uploaded_images(db, product, images, service_from(request))
    except Exception as exc:
        db.delete(product)
        db.commit()
        delete_product_directory(product.id)
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product.id))


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
            await add_uploaded_images(db, product, images, service_from(request))
    except Exception as exc:
        product.name = old_name
        db.commit()
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product_id))


@router.post("/products/{product_id}/images", response_model=ProductDetail)
async def upload_images(product_id: int, request: Request, images: list[UploadFile] = File(...), db: Session = Depends(get_db)) -> ProductDetail:
    product = product_or_404(db, product_id)
    if not images:
        raise HTTPException(422, "Envie ao menos uma imagem")
    try:
        await add_uploaded_images(db, product, images, service_from(request))
    except Exception as exc:
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product_id))


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


def regenerate_product(db: Session, product: Product, service: EmbeddingService) -> None:
    originals = {image.id: image.embedding for image in product.images}
    try:
        for image in product.images:
            image.embedding = embedding_to_json(service.generate_embedding(config.BASE_DIR / image.file_path))
        db.commit()
    except Exception:
        db.rollback()
        for image in product.images:
            image.embedding = originals[image.id]
        raise


@router.post("/products/{product_id}/regenerate-embeddings", response_model=ProductDetail)
def regenerate_embeddings(product_id: int, request: Request, db: Session = Depends(get_db)) -> ProductDetail:
    product = product_or_404(db, product_id)
    try:
        regenerate_product(db, product, service_from(request))
    except Exception as exc:
        raise translate_image_error(exc) from exc
    return detail(product_or_404(db, product_id))


@router.post("/regenerate-all-embeddings")
def regenerate_all(request: Request, db: Session = Depends(get_db)) -> dict[str, int]:
    products = db.scalars(select(Product).options(selectinload(Product.images))).all()
    try:
        for product in products:
            for image in product.images:
                image.embedding = embedding_to_json(service_from(request).generate_embedding(config.BASE_DIR / image.file_path))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise translate_image_error(exc) from exc
    return {"products": len(products), "embeddings": sum(len(p.images) for p in products)}
