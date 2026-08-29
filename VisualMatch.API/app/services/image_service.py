import io
import json
import shutil
import uuid
from pathlib import Path

import numpy as np
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app import config
from app.models import Product, ProductImage
from app.services.embedding_service import EmbeddingService


class InvalidImageError(ValueError):
    pass


def embedding_to_json(value: np.ndarray) -> str:
    return json.dumps(value.astype(np.float32).tolist(), separators=(",", ":"), allow_nan=False)


def embedding_from_json(value: str) -> list[float]:
    return [float(item) for item in json.loads(value)]


async def add_uploaded_images(db: Session, product: Product, uploads: list[UploadFile], embedding_service: EmbeddingService) -> list[ProductImage]:
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
            embedding = embedding_service.generate_embedding(path)
            record = ProductImage(product_id=product.id, file_path=str(path.relative_to(config.BASE_DIR)), file_name=(upload.filename or path.name)[:255], embedding=embedding_to_json(embedding))
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
