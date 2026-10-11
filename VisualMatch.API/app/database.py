from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, LEGACY_MODEL_ID


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def upgrade_schema(bind: Engine) -> None:
    """Creates missing tables/columns and moves single-model embeddings into image_embeddings."""
    from app import models  # noqa: F401  registers every table on Base.metadata

    Base.metadata.create_all(bind)
    with bind.begin() as connection:
        if "model_md5" not in {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(image_embeddings)")}:
            connection.exec_driver_sql("ALTER TABLE image_embeddings ADD COLUMN model_md5 VARCHAR(32)")
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(product_images)")}
        if "embedding" not in columns:
            return
        connection.execute(
            text(
                "INSERT OR IGNORE INTO image_embeddings (image_id, model_id, embedding, created_at) "
                "SELECT id, :model_id, embedding, created_at FROM product_images"
            ),
            {"model_id": LEGACY_MODEL_ID},
        )
        connection.exec_driver_sql("ALTER TABLE product_images DROP COLUMN embedding")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
