from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "image-encoder.onnx"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'products.db'}"

MODEL_NAME = "mobilenetv2"
MODEL_VERSION = "1.0"
INPUT_WIDTH = 224
INPUT_HEIGHT = 224
COLOR_FORMAT = "RGB"
RESIZE_MODE = "stretch"
RESIZE_ALGORITHM = "bilinear"
NORMALIZATION_TYPE = "imagenet_mean_std"
NORMALIZATION_MEAN = [0.485, 0.456, 0.406]
NORMALIZATION_STD = [0.229, 0.224, 0.225]
NORMALIZATION_LOCATION = "onnx_graph"
L2_NORMALIZE = True
MAX_IMAGE_BYTES = 15 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def ensure_directories() -> None:
    for directory in (DATA_DIR, IMAGES_DIR, MODELS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
