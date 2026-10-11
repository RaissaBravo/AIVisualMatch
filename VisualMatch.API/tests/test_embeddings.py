from pathlib import Path

import numpy as np
import pytest

from app import config
from app.services.embedding_service import EmbeddingService


@pytest.mark.parametrize("spec", config.MODELS.values(), ids=list(config.MODELS))
def test_real_embedding_is_deterministic(spec, jpeg_bytes, tmp_path):
    if not spec.path.exists():
        pytest.skip(f"{spec.file_name} ainda não exportado")
    path = tmp_path / "sample.jpg"
    path.write_bytes(jpeg_bytes)
    service = EmbeddingService(spec)
    first = service.generate_embedding(path)
    second = service.generate_embedding(path)
    info = service.get_model_info()
    assert first.dtype == np.float32
    assert first.size == info["embedding_dimension"] == spec.embedding_dimension
    assert info["input_width"] == spec.input_size and info["input_layout"] == "NHWC" and info["input_dtype"] == "uint8"
    assert info["model_size"] == spec.path.stat().st_size and len(info["model_md5"]) == 32
    assert np.isfinite(first).all()
    assert np.allclose(first, second, rtol=1e-6, atol=1e-7)
    assert np.isclose(np.linalg.norm(first), 1.0, atol=1e-5)


def test_missing_model_is_reported(tmp_path):
    service = EmbeddingService(config.MODELS["mobilenetv2"], tmp_path / "missing.onnx")
    info = service.get_model_info()
    assert info["available"] is False
    assert "não encontrado" in info["error"]
