"""Export the registered image encoders to ONNX with the shared uint8 NHWC contract.

Every graph receives uint8 RGB pixels [N, H, W, 3] and performs the cast, /255,
NHWC->NCHW and the model's own mean/std normalization internally, so the API and
the app feed every model exactly the same tensor and only the input size varies.

The weights come from their official sources (torchvision, timm and open_clip on the
Hugging Face Hub), so each machine accepts the model licenses itself and the ONNX
files stay out of git.

    python scripts/export_models.py                 # every registered model still missing
    python scripts/export_models.py dinov2-small    # re-export specific models
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import MODELS, ModelSpec  # noqa: E402


class GlobalAveragePool(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x.mean(dim=(2, 3))


class UInt8Encoder(nn.Module):
    def __init__(self, backbone: nn.Module, mean: list[float], std: list[float]) -> None:
        super().__init__()
        self.backbone = backbone
        self.register_buffer("mean", torch.tensor(mean, dtype=torch.float32).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(std, dtype=torch.float32).view(1, 3, 1, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(torch.float32).div(255.0).permute(0, 3, 1, 2)
        return self.backbone((x - self.mean) / self.std).flatten(1)


def build_mobilenetv2() -> nn.Module:
    """torchvision ImageNet features + global average pooling (1280-D), no classifier."""
    from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

    model = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V2)
    return nn.Sequential(model.features, GlobalAveragePool())


def build_mobilenetv3() -> nn.Module:
    """torchvision MobileNetV3-Large features + global average pooling (960-D), before the classifier.

    On the catalog the pooled 960-D features beat the 1280-D pre-logits layer (top-1 42.1% vs 40.0%).
    """
    from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large

    model = mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.IMAGENET1K_V2)
    return nn.Sequential(model.features, GlobalAveragePool())


def build_dinov2_small() -> nn.Module:
    """DINOv2 ViT-S/14 CLS token (384-D); timm resamples the position embedding to 224 at load time."""
    import timm

    return timm.create_model("vit_small_patch14_dinov2.lvd142m", pretrained=True, img_size=224, num_classes=0)


def build_mobileclip2_s0() -> nn.Module:
    """MobileCLIP2-S0 image tower with its CLIP projection (512-D), reparameterized for inference."""
    import open_clip
    from timm.utils import reparameterize_model

    model = open_clip.create_model("MobileCLIP2-S0", pretrained="dfndr2b")
    return reparameterize_model(model.visual.eval())


BUILDERS = {"mobilenetv2": build_mobilenetv2, "mobilenetv3": build_mobilenetv3, "dinov2-small": build_dinov2_small, "mobileclip2-s0": build_mobileclip2_s0}


def export(spec: ModelSpec, output: Path) -> None:
    encoder = UInt8Encoder(BUILDERS[spec.id]().eval(), spec.mean, spec.std).eval()
    sample = torch.randint(0, 256, (1, spec.input_size, spec.input_size, 3), dtype=torch.uint8)
    with torch.no_grad():
        expected = encoder(sample).numpy()
    output.parent.mkdir(parents=True, exist_ok=True)
    # The legacy exporter keeps everything in a single self-contained file, which the app downloads as is.
    torch.onnx.export(
        encoder, (sample,), output, input_names=["input"], output_names=["embedding"], opset_version=17,
        dynamo=False, external_data=False, dynamic_axes={"input": {0: "batch"}, "embedding": {0: "batch"}},
    )
    verify(output, sample.numpy(), expected, spec)


def verify(output: Path, sample: np.ndarray, expected: np.ndarray, spec: ModelSpec) -> None:
    import onnxruntime as ort

    session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
    actual = session.run(None, {"input": sample})[0]
    if actual.shape != (1, spec.embedding_dimension):
        raise SystemExit(f"{spec.id}: saída {actual.shape}, esperado (1, {spec.embedding_dimension})")
    cosine = float(np.dot(actual[0], expected[0]) / (np.linalg.norm(actual[0]) * np.linalg.norm(expected[0])))
    if cosine < 0.9999:
        raise SystemExit(f"{spec.id}: ONNX diverge do PyTorch (cosseno {cosine:.6f})")
    size_mb = output.stat().st_size / 1024 / 1024
    print(f"{spec.id}: {output} ({size_mb:.1f} MB, {actual.shape[1]}-D, cosseno PyTorch/ONNX {cosine:.6f})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("models", nargs="*", choices=sorted(BUILDERS), help="ids do registro em app/config.py; sem ids, exporta os que faltam")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models")
    args = parser.parse_args()
    model_ids = args.models or [spec.id for spec in MODELS.values() if not (args.output_dir / spec.file_name).exists()]
    if not model_ids:
        print(f"Todos os modelos registrados já existem em {args.output_dir}")
    for model_id in model_ids:
        spec = MODELS[model_id]
        export(spec, args.output_dir / spec.file_name)


if __name__ == "__main__":
    main()
