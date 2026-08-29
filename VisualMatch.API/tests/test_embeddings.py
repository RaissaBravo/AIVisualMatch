from pathlib import Path

import numpy as np
import pytest

from app import config
from app.services.embedding_service import EmbeddingService


@pytest.mark.skipif(not config.MODEL_PATH.exists(), reason="Modelo ONNX ainda não adicionado")
def test_real_embedding_is_deterministic(jpeg_bytes, tmp_path):
    path = tmp_path / "sample.jpg"
    path.write_bytes(jpeg_bytes)
    service = EmbeddingService()
    first = service.generate_embedding(path)
    second = service.generate_embedding(path)
    assert first.dtype == np.float32
    assert first.size == service.get_model_info()["embedding_dimension"]
    assert np.isfinite(first).all()
    assert np.allclose(first, second, rtol=1e-6, atol=1e-7)
    assert np.isclose(np.linalg.norm(first), 1.0, atol=1e-5)


def test_missing_model_is_reported(tmp_path):
    service = EmbeddingService(tmp_path / "missing.onnx")
    info = service.get_model_info()
    assert info["available"] is False
    assert "não encontrado" in info["error"]
