import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import config
from app.database import engine, upgrade_schema
from app.routers import admin, products_api
from app.services.embedding_service import ModelRegistry
from app.services.image_service import generate_all_pending_embeddings

config.ensure_directories()
logger = logging.getLogger("uvicorn.error")


def sync_all_models(models: ModelRegistry) -> None:
    """Generates every loaded model's missing or outdated embeddings before serving requests."""
    for service in models.services.values():
        if not service.available:
            logger.warning("Modelo %s indisponível; embeddings não gerados: %s", service.spec.name, service.load_error)
    started = time.perf_counter()
    with Session(engine, expire_on_commit=False) as db:
        results = generate_all_pending_embeddings(db, models)
    for model_id, (generated, failures) in results.items():
        if generated:
            logger.info("%d embeddings de %s gerados", generated, models.get(model_id).spec.name)
        for failure in failures:
            logger.error("Embedding de %s não gerado: %s", models.get(model_id).spec.name, failure)
    logger.info("Embeddings prontos para %s (%.1f s)", ", ".join(models.get(model_id).spec.name for model_id in results), time.perf_counter() - started)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upgrade_schema(engine)
    app.state.models = ModelRegistry()
    sync_all_models(app.state.models)
    yield


app = FastAPI(title="VisualMatch API", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "app" / "static")), name="static")
app.mount("/images", StaticFiles(directory=str(config.IMAGES_DIR)), name="images")
app.include_router(products_api.router)
app.include_router(admin.router)
