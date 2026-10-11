from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.id"
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    product: Mapped[Product] = relationship(back_populates="images")
    embeddings: Mapped[list["ImageEmbedding"]] = relationship(back_populates="image", cascade="all, delete-orphan")

    def embedding_for(self, model_id: str) -> "ImageEmbedding | None":
        return next((item for item in self.embeddings if item.model_id == model_id), None)


class ImageEmbedding(Base):
    """One vector per image and model, so switching models never discards the others."""

    __tablename__ = "image_embeddings"

    image_id: Mapped[int] = mapped_column(ForeignKey("product_images.id", ondelete="CASCADE"), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    # MD5 of the ONNX file that produced the vector; NULL for rows saved before versioning.
    model_md5: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    image: Mapped[ProductImage] = relationship(back_populates="embeddings")
