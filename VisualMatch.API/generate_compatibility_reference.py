import argparse
import json
from pathlib import Path

from app import config
from app.services.embedding_service import EmbeddingService


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o embedding de referência para comparar API e app.")
    parser.add_argument("model", nargs="?", default=config.DEFAULT_MODEL_ID, choices=sorted(config.MODELS))
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent / "compatibility_test"
    image = directory / "test_image.jpg"
    if not image.exists():
        raise SystemExit(f"Adicione a imagem de referência em {image}")
    service = EmbeddingService(config.MODELS[args.model])
    service.require_model()
    embedding = service.generate_embedding(image)
    (directory / "expected_embedding.json").write_text(json.dumps(embedding.tolist(), separators=(",", ":")), encoding="utf-8")
    (directory / "model_info.json").write_text(json.dumps(service.get_model_info(), indent=2), encoding="utf-8")
    print(f"Referência de {args.model} gerada com {embedding.size} dimensões")


if __name__ == "__main__":
    main()
