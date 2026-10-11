"""Compare the registered encoders on the catalog with leave-one-out retrieval.

Each catalog photo is used as a query against all the other photos, scored exactly
like the app: centroid subtraction, cosine, best reference per product, and a match
only when the winner clears the threshold and beats the runner-up by the margin.
Embeddings are computed in memory; the database is opened read-only. Catalog photos
are not camera frames, so use it to rank models, and calibrate thresholds on device.

    python scripts/evaluate_models.py [--threshold 0.45] [--margin 0.08]
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402

MIN_REFERENCES_FOR_CENTERING = 3


def catalog() -> tuple[list[Path], np.ndarray]:
    connection = sqlite3.connect(f"file:{config.DATA_DIR / 'products.db'}?mode=ro", uri=True)
    try:
        rows = connection.execute("SELECT file_path, product_id FROM product_images ORDER BY id").fetchall()
    finally:
        connection.close()
    return [config.BASE_DIR / path for path, _ in rows], np.array([product for _, product in rows])


def centered(embeddings: np.ndarray) -> np.ndarray:
    mean = embeddings.mean(axis=0) if len(embeddings) >= MIN_REFERENCES_FOR_CENTERING else 0.0
    vectors = embeddings - mean
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def leave_one_out(vectors: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per query: top-1 score, runner-up score and whether top-1 is the right product."""
    similarity = vectors @ vectors.T
    np.fill_diagonal(similarity, -np.inf)
    products = np.unique(labels)
    scores = np.stack([similarity[:, labels == product].max(axis=1) for product in products], axis=1)
    # A product's only photo has nothing left to match against.
    queryable = np.isfinite(scores[np.arange(len(labels)), np.searchsorted(products, labels)])
    scores, labels = scores[queryable], labels[queryable]
    order = np.argsort(-scores, axis=1)
    rows = np.arange(len(scores))
    return scores[rows, order[:, 0]], scores[rows, order[:, 1]], products[order[:, 0]] == labels


def rates(top: np.ndarray, runner_up: np.ndarray, correct: np.ndarray, threshold: float, margin: float) -> tuple[float, float]:
    accepted = (top >= threshold) & (top - runner_up >= margin)
    return float((accepted & correct).mean()), float((accepted & ~correct).mean())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--threshold", type=float, default=0.45, help="MATCH_THRESHOLD usado no app")
    parser.add_argument("--margin", type=float, default=0.08, help="MATCH_MARGIN usado no app")
    args = parser.parse_args()
    paths, labels = catalog()
    print(f"{len(paths)} imagens de {len(np.unique(labels))} produtos; limiar {args.threshold}, margem {args.margin}\n")
    print(f"{'modelo':<16}{'top-1':>8}{'margem p50':>12}{'match certo':>13}{'match errado':>14}")
    for spec in config.MODELS.values():
        service = EmbeddingService(spec)
        if not service.available:
            print(f"{spec.id:<16}indisponível: {service.load_error}")
            continue
        embeddings = np.stack([service.generate_embedding(path) for path in paths])
        top, runner_up, correct = leave_one_out(centered(embeddings), labels)
        right, wrong = rates(top, runner_up, correct, args.threshold, args.margin)
        print(f"{spec.id:<16}{correct.mean():>8.1%}{np.median(top - runner_up):>12.3f}{right:>13.1%}{wrong:>14.1%}")


if __name__ == "__main__":
    main()
