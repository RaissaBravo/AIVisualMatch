from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"
MODELS_DIR = BASE_DIR / "models"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'products.db'}"

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


@dataclass(frozen=True)
class ModelSpec:
    """Everything the API and the app must agree on for one image encoder."""

    id: str
    name: str
    version: str
    input_size: int
    embedding_dimension: int
    normalization_type: str
    mean: tuple[float, float, float]
    std: tuple[float, float, float]
    license: str

    @property
    def file_name(self) -> str:
        return f"{self.id}.onnx"

    @property
    def path(self) -> Path:
        return MODELS_DIR / self.file_name


MODELS = {
    spec.id: spec
    for spec in (
        ModelSpec("mobilenetv2", "MobileNetV2", "1.0", 224, 1280, "imagenet_mean_std", IMAGENET_MEAN, IMAGENET_STD, "BSD-3-Clause (torchvision)"),
        ModelSpec("mobilenetv3", "MobileNetV3-Large", "1.0", 224, 960, "imagenet_mean_std", IMAGENET_MEAN, IMAGENET_STD, "BSD-3-Clause (torchvision)"),
        ModelSpec("dinov2-small", "DINOv2-Small", "1.0", 224, 384, "imagenet_mean_std", IMAGENET_MEAN, IMAGENET_STD, "Apache-2.0"),
        ModelSpec("mobileclip2-s0", "MobileCLIP2-S0", "1.0", 256, 512, "scale_only", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), "Apple AMLR (somente pesquisa, não comercial)"),
    )
}
# Embeddings stored before multi-model support were all produced by this encoder.
LEGACY_MODEL_ID = "mobilenetv2"
# The API keeps every model ready and the app picks one; requests without ?model= get this one.
DEFAULT_MODEL_ID = next(iter(MODELS))

COLOR_FORMAT = "RGB"
RESIZE_MODE = "stretch"
RESIZE_ALGORITHM = "bilinear"
NORMALIZATION_LOCATION = "onnx_graph"
L2_NORMALIZE = True
MAX_IMAGE_BYTES = 15 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def ensure_directories() -> None:
    for directory in (DATA_DIR, IMAGES_DIR, MODELS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
