import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.database import Base, get_db
from app.main import app


class FakeEmbeddingService:
    def generate_embedding(self, image_path: Path) -> np.ndarray:
        with Image.open(image_path) as image:
            rgb = np.asarray(image.convert("RGB").resize((8, 8)), dtype=np.float32)
        vector = np.array([rgb.mean(), rgb.std(), rgb[..., 0].mean(), rgb[..., 1].mean()], dtype=np.float32)
        return vector / np.linalg.norm(vector)

    def get_model_info(self) -> dict:
        return {"available": True, "embedding_dimension": 4, "input_layout": "NCHW"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    images_path = tmp_path / "images"
    images_path.mkdir()
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "IMAGES_DIR", images_path)

    def override_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        app.state.embedding_service = FakeEmbeddingService()
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (24, 18), (30, 120, 220)).save(buffer, format="JPEG")
    return buffer.getvalue()
