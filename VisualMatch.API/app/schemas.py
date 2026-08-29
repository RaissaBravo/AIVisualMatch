from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProductUpdate(ProductCreate):
    pass


class ProductListItem(BaseModel):
    id: int
    name: str
    embeddings: list[list[float]]


class ProductImageDetail(BaseModel):
    id: int
    file_name: str
    url: str
    embedding: list[float]
    created_at: datetime


class ProductDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    images: list[ProductImageDetail]
    created_at: datetime
    updated_at: datetime
