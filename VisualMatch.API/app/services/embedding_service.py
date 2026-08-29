from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app import config


class ModelUnavailableError(RuntimeError):
    pass


class EmbeddingError(RuntimeError):
    pass


class EmbeddingService:
    """Single-session ONNX feature extractor with an explicit, reproducible pipeline."""

    def __init__(self, model_path: Path = config.MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self.session: Any | None = None
        self.input_name: str | None = None
        self.output_name: str | None = None
        self.input_shape: list[Any] | None = None
        self.output_shape: list[Any] | None = None
        self.input_layout: str | None = None
        self.input_dtype: str | None = None
        self.embedding_dimension: int | None = None
        self.load_error: str | None = None
        if self.model_path.exists():
            self._load_model()
        else:
            self.load_error = f"Modelo ONNX não encontrado em {self.model_path}"

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
        for actual, expected, label in ((height, config.INPUT_HEIGHT, "altura"), (width, config.INPUT_WIDTH, "largura")):
            if isinstance(actual, int) and actual != expected:
                raise ValueError(f"{label} do modelo é {actual}, configuração exige {expected}")

    def require_model(self) -> None:
        if self.session is None:
            raise ModelUnavailableError(self.load_error or "Modelo ONNX indisponível")

    def preprocess_image(self, image_path: str | Path) -> np.ndarray:
        self.require_model()
        try:
            with Image.open(image_path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image = image.resize((config.INPUT_WIDTH, config.INPUT_HEIGHT), Image.Resampling.BILINEAR)
                tensor = np.asarray(image, dtype=np.uint8)
        except Exception as exc:
            raise EmbeddingError(f"Falha ao processar imagem: {exc}") from exc
        if self.input_dtype == "float32":
            tensor = tensor.astype(np.float32) / np.float32(255.0)
            mean = np.asarray(config.NORMALIZATION_MEAN, dtype=np.float32)
            std = np.asarray(config.NORMALIZATION_STD, dtype=np.float32)
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
        return {
            "model": config.MODEL_NAME, "version": config.MODEL_VERSION,
            "model_file": self.model_path.name, "available": self.session is not None,
            "error": self.load_error, "input_name": self.input_name, "output_name": self.output_name,
            "input_shape": self.input_shape, "output_shape": self.output_shape,
            "input_width": config.INPUT_WIDTH, "input_height": config.INPUT_HEIGHT,
            "input_layout": self.input_layout, "color_format": config.COLOR_FORMAT,
            "input_dtype": self.input_dtype, "resize_mode": config.RESIZE_MODE,
            "resize_algorithm": config.RESIZE_ALGORITHM,
            "normalization": {"type": config.NORMALIZATION_TYPE, "location": config.NORMALIZATION_LOCATION if self.input_dtype == "uint8" else "backend", "scale": "pixel / 255.0", "mean": config.NORMALIZATION_MEAN, "std": config.NORMALIZATION_STD},
            "l2_normalization": config.L2_NORMALIZE, "embedding_dimension": self.embedding_dimension,
        }
