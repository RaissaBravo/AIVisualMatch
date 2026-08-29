import json
from pathlib import Path

from app.services.embedding_service import EmbeddingService


def main() -> None:
    directory = Path(__file__).resolve().parent / "compatibility_test"
    image = directory / "test_image.jpg"
    if not image.exists():
        raise SystemExit(f"Adicione a imagem de referência em {image}")
    service = EmbeddingService()
    service.require_model()
    embedding = service.generate_embedding(image)
    (directory / "expected_embedding.json").write_text(json.dumps(embedding.tolist(), separators=(",", ":")), encoding="utf-8")
    (directory / "model_info.json").write_text(json.dumps(service.get_model_info(), indent=2), encoding="utf-8")
    print(f"Referência gerada com {embedding.size} dimensões")


if __name__ == "__main__":
    main()
