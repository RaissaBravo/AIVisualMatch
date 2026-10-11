import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app import config
from app.config import ModelSpec


class ModelUnavailableError(RuntimeError):
    pass


class UnknownModelError(KeyError):
    pass


class EmbeddingError(RuntimeError):
    pass


def file_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class EmbeddingService:
    """Single-session ONNX feature extractor with an explicit, reproducible pipeline."""

    def __init__(self, spec: ModelSpec, model_path: Path | None = None) -> None:
        self.spec = spec
        self.model_path = Path(model_path or spec.path)
        self.session: Any | None = None
        self.input_name: str | None = None
        self.output_name: str | None = None
        self.input_shape: list[Any] | None = None
        self.output_shape: list[Any] | None = None
        self.input_layout: str | None = None
        self.input_dtype: str | None = None
        self.embedding_dimension: int | None = None
        self.file_size: int | None = None
        self.file_md5: str | None = None
        self.load_error: str | None = None
        if self.model_path.exists():
            self._load_model()
        else:
            self.load_error = f"Modelo ONNX não encontrado em {self.model_path}; gere com: python scripts/export_models.py {spec.id}"

    @property
    def available(self) -> bool:
        return self.session is not None

    def _load_model(self) -> None:
        try:
            import onnxruntime as ort

            self.session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
            inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
            if len(inputs) != 1 or len(outputs) != 1:
                raise ValueError("O modelo deve possuir exatamente uma entrada e uma saída de features")
            input_meta, output_meta = inputs[0], outputs[0]
            supported_types = {"tensor(float)": "float32", "tensor(uint8)": "uint8"}
            if input_meta.type not in supported_types:
                raise ValueError(f"Input deve ser float32 ou uint8; recebido {input_meta.type}")
            self.input_dtype = supported_types[input_meta.type]
            self.input_name, self.output_name = input_meta.name, output_meta.name
            self.input_shape, self.output_shape = list(input_meta.shape), list(output_meta.shape)
            self.input_layout = self._detect_layout(self.input_shape)
            self._validate_spatial_shape()
            dim = self.output_shape[-1] if self.output_shape else None
            self.embedding_dimension = int(dim) if isinstance(dim, int) else None
            if self.embedding_dimension not in (None, self.spec.embedding_dimension):
                raise ValueError(f"saída do modelo tem {self.embedding_dimension} dimensões, registro exige {self.spec.embedding_dimension}")
            self.file_size = self.model_path.stat().st_size
            self.file_md5 = file_md5(self.model_path)
            self.load_error = None
        except Exception as exc:
            self.session = None
            self.load_error = f"Modelo ONNX inválido: {exc}"

    @staticmethod
    def _detect_layout(shape: list[Any]) -> str:
        if len(shape) != 4:
            raise ValueError(f"Input deve ter 4 dimensões; recebido {shape}")
        if shape[1] == 3:
            return "NCHW"
        if shape[3] == 3:
            return "NHWC"
        raise ValueError(f"Não foi possível detectar canal RGB no shape {shape}")

    def _validate_spatial_shape(self) -> None:
        assert self.input_shape and self.input_layout
        height, width = ((self.input_shape[2], self.input_shape[3]) if self.input_layout == "NCHW" else (self.input_shape[1], self.input_shape[2]))
        for actual, label in ((height, "altura"), (width, "largura")):
            if isinstance(actual, int) and actual != self.spec.input_size:
                raise ValueError(f"{label} do modelo é {actual}, registro exige {self.spec.input_size}")

    def require_model(self) -> None:
        if self.session is None:
            raise ModelUnavailableError(self.load_error or "Modelo ONNX indisponível")

    def preprocess_image(self, image_path: str | Path) -> np.ndarray:
        self.require_model()
        size = self.spec.input_size
        try:
            with Image.open(image_path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image = image.resize((size, size), Image.Resampling.BILINEAR)
                tensor = np.asarray(image, dtype=np.uint8)
        except Exception as exc:
            raise EmbeddingError(f"Falha ao processar imagem: {exc}") from exc
        if self.input_dtype == "float32":
            tensor = tensor.astype(np.float32) / np.float32(255.0)
            mean = np.asarray(self.spec.mean, dtype=np.float32)
            std = np.asarray(self.spec.std, dtype=np.float32)
            tensor = (tensor - mean) / std
        if self.input_layout == "NCHW":
            tensor = np.transpose(tensor, (2, 0, 1))
        dtype = np.uint8 if self.input_dtype == "uint8" else np.float32
        return np.ascontiguousarray(tensor[np.newaxis, ...], dtype=dtype)

    def generate_embedding(self, image_path: str | Path) -> np.ndarray:
        tensor = self.preprocess_image(image_path)
        try:
            assert self.session and self.input_name and self.output_name
            raw = self.session.run([self.output_name], {self.input_name: tensor})[0]
            embedding = np.asarray(raw, dtype=np.float32).reshape(-1)
        except Exception as exc:
            raise EmbeddingError(f"Falha na inferência ONNX: {exc}") from exc
        if not embedding.size or not np.isfinite(embedding).all():
            raise EmbeddingError("O modelo retornou embedding vazio ou não finito")
        if config.L2_NORMALIZE:
            norm = float(np.linalg.norm(embedding))
            if norm <= 0.0:
                raise EmbeddingError("Não é possível normalizar embedding com norma zero")
            embedding = embedding / np.float32(norm)
        if self.embedding_dimension is None:
            self.embedding_dimension = int(embedding.size)
        elif embedding.size != self.embedding_dimension:
            raise EmbeddingError("Dimensão do embedding diverge do metadado do modelo")
        return np.asarray(embedding, dtype=np.float32)

    def get_model_info(self) -> dict[str, Any]:
        spec = self.spec
        return {
            "model": spec.id, "name": spec.name, "version": spec.version, "license": spec.license,
            "model_file": self.model_path.name, "model_url": f"/api/models/{spec.id}/file",
            "model_size": self.file_size, "model_md5": self.file_md5,
            "available": self.session is not None,
            "error": self.load_error, "input_name": self.input_name, "output_name": self.output_name,
            "input_shape": self.input_shape, "output_shape": self.output_shape,
            "input_width": spec.input_size, "input_height": spec.input_size,
            "input_layout": self.input_layout, "color_format": config.COLOR_FORMAT,
            "input_dtype": self.input_dtype, "resize_mode": config.RESIZE_MODE,
            "resize_algorithm": config.RESIZE_ALGORITHM,
            "normalization": {"type": spec.normalization_type, "location": config.NORMALIZATION_LOCATION if self.input_dtype == "uint8" else "backend", "scale": "pixel / 255.0", "mean": list(spec.mean), "std": list(spec.std)},
            "l2_normalization": config.L2_NORMALIZE, "embedding_dimension": self.embedding_dimension,
        }


class ModelRegistry:
    """One EmbeddingService per registered model; every loaded model embeds every image."""

    def __init__(self, services: Iterable[EmbeddingService] | None = None, default_id: str = config.DEFAULT_MODEL_ID) -> None:
        if services is None:
            services = [EmbeddingService(spec) for spec in config.MODELS.values()]
        self.services = {service.spec.id: service for service in services}
        if default_id not in self.services:
            raise ValueError(f"Modelo padrão {default_id!r} não está registrado; opções: {', '.join(self.services)}")
        self.default_id = default_id

    @property
    def available(self) -> list[EmbeddingService]:
        return [service for service in self.services.values() if service.available]

    def get(self, model_id: str | None = None) -> EmbeddingService:
        service = self.services.get(model_id or self.default_id)
        if service is None:
            raise UnknownModelError(f"Modelo {model_id!r} não registrado")
        return service

    def generate_embeddings(self, image_path: str | Path, model_id: str | None = None) -> dict[str, np.ndarray]:
        """Embeds with one model, or with every loaded one so the app can switch freely."""
        if model_id:
            targets = [self.get(model_id)]
        else:
            targets = self.available
            if not targets:
                raise ModelUnavailableError("Nenhum modelo ONNX disponível; gere-os com: python scripts/export_models.py")
        return {service.spec.id: service.generate_embedding(image_path) for service in targets}
