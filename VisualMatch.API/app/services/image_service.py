import io
import json
import shutil
import uuid
from pathlib import Path

import numpy as np
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import config
from app.models import ImageEmbedding, Product, ProductImage
from app.services.embedding_service import EmbeddingError, EmbeddingService, ModelRegistry


class InvalidImageError(ValueError):
    pass


def embedding_to_json(value: np.ndarray) -> str:
    return json.dumps(value.astype(np.float32).tolist(), separators=(",", ":"), allow_nan=False)


def embedding_from_json(value: str) -> list[float]:
    return [float(item) for item in json.loads(value)]


def store_embeddings(image: ProductImage, embeddings: dict[str, np.ndarray], models: ModelRegistry) -> None:
    for model_id, vector in embeddings.items():
        record = image.embedding_for(model_id)
        if record is None:
            record = ImageEmbedding(model_id=model_id)
            image.embeddings.append(record)
        record.embedding = embedding_to_json(vector)
        record.model_md5 = models.get(model_id).file_md5


def is_current(stored_md5: str | None, service: EmbeddingService) -> bool:
    """Rows saved before versioning have no md5 and are trusted as made by the current file."""
    return stored_md5 is None or stored_md5 == service.file_md5


def embedding_state(image: ProductImage, service: EmbeddingService) -> str:
    record = image.embedding_for(service.spec.id)
    if record is None:
        return "missing"
    return "current" if is_current(record.model_md5, service) else "outdated"


def generate_pending_embeddings(db: Session, models: ModelRegistry, model_id: str) -> tuple[int, list[str]]:
    """Fills one model's missing or outdated embeddings; an unreadable image is reported, not fatal."""
    service = models.get(model_id)
    service.require_model()
    images = db.scalars(select(ProductImage).options(selectinload(ProductImage.embeddings)).order_by(ProductImage.id)).all()
    generated, failures = 0, []
    for image in images:
        if embedding_state(image, service) == "current":
            continue
        try:
            store_embeddings(image, {model_id: service.generate_embedding(config.BASE_DIR / image.file_path)}, models)
            generated += 1
        except EmbeddingError as exc:
            failures.append(f"{image.file_path}: {exc}")
    db.commit()
    return generated, failures


def generate_all_pending_embeddings(db: Session, models: ModelRegistry) -> dict[str, tuple[int, list[str]]]:
    """Keeps every loaded model ready, so the app can switch to any of them."""
    return {service.spec.id: generate_pending_embeddings(db, models, service.spec.id) for service in models.available}


async def add_uploaded_images(db: Session, product: Product, uploads: list[UploadFile], models: ModelRegistry) -> list[ProductImage]:
    created_paths: list[Path] = []
    records: list[ProductImage] = []
    product_dir = config.IMAGES_DIR / str(product.id)
    try:
        for upload in uploads:
            data = await upload.read(config.MAX_IMAGE_BYTES + 1)
            if not data:
                raise InvalidImageError("Arquivo de imagem vazio")
            if len(data) > config.MAX_IMAGE_BYTES:
                raise InvalidImageError(f"Imagem excede o limite de {config.MAX_IMAGE_BYTES // (1024 * 1024)} MB")
            try:
                with Image.open(io.BytesIO(data)) as probe:
                    image_format = probe.format
                    probe.verify()
            except (UnidentifiedImageError, OSError) as exc:
                raise InvalidImageError("Arquivo corrompido ou não é uma imagem válida") from exc
            if image_format not in config.ALLOWED_FORMATS:
                raise InvalidImageError("Formato não suportado; use JPEG, PNG ou WEBP")
            product_dir.mkdir(parents=True, exist_ok=True)
            path = product_dir / f"{uuid.uuid4().hex}{config.ALLOWED_FORMATS[image_format]}"
            try:
                path.write_bytes(data)
            except OSError as exc:
                raise InvalidImageError(f"Não foi possível salvar a imagem: {exc}") from exc
            created_paths.append(path)
            embeddings = models.generate_embeddings(path)
            record = ProductImage(product_id=product.id, file_path=str(path.relative_to(config.BASE_DIR)), file_name=(upload.filename or path.name)[:255], embeddings=[])
            store_embeddings(record, embeddings, models)
            db.add(record)
            records.append(record)
        db.commit()
        for record in records:
            db.refresh(record)
        return records
    except Exception:
        db.rollback()
        for path in created_paths:
            path.unlink(missing_ok=True)
        if product_dir.exists() and not any(product_dir.iterdir()):
            product_dir.rmdir()
        raise


def delete_image_file(record: ProductImage) -> None:
    path = (config.BASE_DIR / record.file_path).resolve()
    images_root = config.IMAGES_DIR.resolve()
    if path.is_relative_to(images_root):
        path.unlink(missing_ok=True)


def delete_product_directory(product_id: int) -> None:
    directory = (config.IMAGES_DIR / str(product_id)).resolve()
    if directory.parent == config.IMAGES_DIR.resolve() and directory.exists():
        shutil.rmtree(directory)
