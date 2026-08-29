"""Export torchvision MobileNetV2 features (1280-D), without classifier logits."""
from pathlib import Path

import torch
from torch import nn
from torchvision.models import MobileNet_V2_Weights, mobilenet_v2


class MobileNetV2Features(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        model = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V2)
        self.features = model.features
        self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(torch.float32).div(255.0).permute(0, 3, 1, 2)
        x = (x - self.mean) / self.std
        x = self.features(x)
        return x.mean(dim=(2, 3))


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    output = root / "models" / "image-encoder.onnx"
    output.parent.mkdir(parents=True, exist_ok=True)
    model = MobileNetV2Features().eval()
    torch.onnx.export(model, torch.zeros(1, 224, 224, 3, dtype=torch.uint8), output, input_names=["input"], output_names=["embedding"], opset_version=17, dynamic_axes={"input": {0: "batch"}, "embedding": {0: "batch"}})
    print(f"Modelo exportado: {output}")


if __name__ == "__main__":
    main()
