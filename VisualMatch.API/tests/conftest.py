import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.config import ModelSpec
from app.database import Base, get_db
from app.main import app
from app.services.embedding_service import ModelRegistry, ModelUnavailableError


def fake_spec(model_id: str) -> ModelSpec:
    return ModelSpec(model_id, model_id.upper(), "1.0", 8, 4, "scale_only", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), "test")


class FakeEmbeddingService:
    """Deterministic extractor; `reverse` makes a second model produce distinguishable vectors."""

    def __init__(self, model_id: str, reverse: bool = False) -> None:
        self.spec = fake_spec(model_id)
        self.reverse = reverse
        self.available = True
        self.model_path = Path("missing.onnx")
        self.load_error: str | None = None
        self.file_md5: str | None = f"md5-{model_id}"

    def require_model(self) -> None:
        if not self.available:
            raise ModelUnavailableError("Modelo falso indisponível")

    def generate_embedding(self, image_path: Path) -> np.ndarray:
        self.require_model()
        with Image.open(image_path) as image:
            rgb = np.asarray(image.convert("RGB").resize((8, 8)), dtype=np.float32)
        vector = np.array([rgb.mean(), rgb.std(), rgb[..., 0].mean(), rgb[..., 1].mean()], dtype=np.float32)
        vector = vector[::-1] if self.reverse else vector
        return vector / np.linalg.norm(vector)

    def get_model_info(self) -> dict:
        spec = self.spec
        return {"model": spec.id, "name": spec.name, "license": spec.license, "available": self.available, "error": self.load_error, "embedding_dimension": 4, "input_width": spec.input_size, "input_height": spec.input_size, "input_layout": "NCHW"}


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
    # Keeps the lifespan away from the real database and the real ONNX files.
    monkeypatch.setattr("app.main.engine", test_engine)
    models = ModelRegistry([FakeEmbeddingService("fake"), FakeEmbeddingService("fake-b", reverse=True)], default_id="fake")
    monkeypatch.setattr("app.main.ModelRegistry", lambda: models)

    def override_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (24, 18), (30, 120, 220)).save(buffer, format="JPEG")
    return buffer.getvalue()
