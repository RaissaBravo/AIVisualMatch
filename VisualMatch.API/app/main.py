from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config
from app.database import Base, engine
from app.routers import admin, products_api
from app.services.embedding_service import EmbeddingService

config.ensure_directories()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    app.state.embedding_service = EmbeddingService()
    yield


app = FastAPI(title="VisualMatch API", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "app" / "static")), name="static")
app.mount("/images", StaticFiles(directory=str(config.IMAGES_DIR)), name="images")
app.include_router(products_api.router)
app.include_router(admin.router)
