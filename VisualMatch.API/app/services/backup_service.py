import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session

from app import config

DATABASE_IN_ZIP = "data/products.db"
IMAGES_IN_ZIP = "images"
MAX_FILES = 10_000
MAX_UNCOMPRESSED_SIZE = 2 * 1024 * 1024 * 1024


class InvalidBackupError(ValueError):
    pass


def database_path(db: Session) -> Path:
    filename = db.get_bind().url.database
    if not filename or filename == ":memory:":
        raise InvalidBackupError("O backup exige um banco SQLite armazenado em arquivo")
    return Path(filename).resolve()


def create_backup(db: Session) -> Path:
    """Gera um snapshot consistente do SQLite e inclui todas as imagens."""
    archive_handle = tempfile.NamedTemporaryFile(prefix="visualmatch-backup-", suffix=".zip", delete=False)
    archive_path = Path(archive_handle.name)
    archive_handle.close()
    snapshot_handle = tempfile.NamedTemporaryFile(prefix="visualmatch-db-", suffix=".db", delete=False)
    snapshot_path = Path(snapshot_handle.name)
    snapshot_handle.close()
    try:
        source = sqlite3.connect(database_path(db))
        target = sqlite3.connect(snapshot_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.write(snapshot_path, DATABASE_IN_ZIP)
            if config.IMAGES_DIR.exists():
                for path in sorted(config.IMAGES_DIR.rglob("*")):
                    if path.is_file():
                        relative = path.relative_to(config.IMAGES_DIR).as_posix()
                        archive.write(path, f"{IMAGES_IN_ZIP}/{relative}")
        return archive_path
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise
    finally:
        snapshot_path.unlink(missing_ok=True)


def validated_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    if len(members) > MAX_FILES:
        raise InvalidBackupError("O ZIP contém arquivos demais")
    if sum(item.file_size for item in members) > MAX_UNCOMPRESSED_SIZE:
        raise InvalidBackupError("O conteúdo descompactado excede 2 GB")
    seen: set[str] = set()
    for item in members:
        path = PurePosixPath(item.filename)
        name = path.as_posix().rstrip("/")
        if path.is_absolute() or ".." in path.parts or not name:
            raise InvalidBackupError("O ZIP contém um caminho inválido")
        if name in seen:
            raise InvalidBackupError(f"Entrada duplicada no ZIP: {name}")
        seen.add(name)
        if stat.S_ISLNK(item.external_attr >> 16):
            raise InvalidBackupError("Links simbólicos não são permitidos")
        if name != DATABASE_IN_ZIP and not name.startswith(f"{IMAGES_IN_ZIP}/"):
            raise InvalidBackupError(f"Arquivo fora do padrão esperado: {name}")
    if DATABASE_IN_ZIP not in seen:
        raise InvalidBackupError(f"O ZIP não contém {DATABASE_IN_ZIP}")
    return members


def extract_backup(archive_path: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for item in validated_members(archive):
                output = destination.joinpath(*PurePosixPath(item.filename).parts)
                if item.is_dir():
                    output.mkdir(parents=True, exist_ok=True)
                else:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source, output.open("wb") as target:
                        shutil.copyfileobj(source, target)
    except (zipfile.BadZipFile, EOFError) as exc:
        raise InvalidBackupError("O arquivo enviado não é um ZIP válido") from exc


def validate_database(path: Path, images_dir: Path) -> None:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise InvalidBackupError("O banco SQLite está corrompido")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"products", "product_images"}.issubset(tables):
                raise InvalidBackupError("O SQLite não possui as tabelas esperadas")
            product_columns = {row[1] for row in connection.execute("PRAGMA table_info(products)")}
            image_columns = {row[1] for row in connection.execute("PRAGMA table_info(product_images)")}
            if not {"id", "name", "created_at", "updated_at"}.issubset(product_columns):
                raise InvalidBackupError("A tabela products não possui o esquema esperado")
            expected_image_columns = {"id", "product_id", "file_path", "file_name", "embedding", "created_at"}
            if not expected_image_columns.issubset(image_columns):
                raise InvalidBackupError("A tabela product_images não possui o esquema esperado")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise InvalidBackupError("O banco possui referências inválidas")
            file_paths = [row[0] for row in connection.execute("SELECT file_path FROM product_images")]
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        raise InvalidBackupError("products.db não é um SQLite válido") from exc
    images_root = images_dir.resolve()
    for filename in file_paths:
        relative = PurePosixPath(filename)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != IMAGES_IN_ZIP:
            raise InvalidBackupError(f"Caminho de imagem inválido no banco: {filename}")
        image_path = images_dir.parent.joinpath(*relative.parts).resolve()
        if not image_path.is_relative_to(images_root) or not image_path.is_file():
            raise InvalidBackupError(f"Imagem não encontrada no ZIP: {filename}")


def restore_backup(db: Session, archive_path: Path) -> None:
    """Valida tudo e só então troca o banco e as imagens, com rollback em falhas."""
    current_database = database_path(db)
    bind = db.get_bind()
    with tempfile.TemporaryDirectory(prefix="visualmatch-restore-") as temporary:
        root = Path(temporary)
        staging = root / "staging"
        staging.mkdir()
        extract_backup(archive_path, staging)
        staged_database = staging / DATABASE_IN_ZIP
        staged_images = staging / IMAGES_IN_ZIP
        staged_images.mkdir(exist_ok=True)
        validate_database(staged_database, staged_images)

        rollback = root / "rollback"
        rollback.mkdir()
        old_database = rollback / "products.db"
        old_images = rollback / IMAGES_IN_ZIP
        db.close()
        bind.dispose()
        current_database.parent.mkdir(parents=True, exist_ok=True)
        config.IMAGES_DIR.parent.mkdir(parents=True, exist_ok=True)
        had_database = current_database.exists()
        had_images = config.IMAGES_DIR.exists()
        try:
            if had_database:
                os.replace(current_database, old_database)
            if had_images:
                os.replace(config.IMAGES_DIR, old_images)
            os.replace(staged_database, current_database)
            os.replace(staged_images, config.IMAGES_DIR)
        except Exception:
            if current_database.exists():
                current_database.unlink()
            if config.IMAGES_DIR.exists():
                shutil.rmtree(config.IMAGES_DIR)
            if had_database and old_database.exists():
                os.replace(old_database, current_database)
            if had_images and old_images.exists():
                os.replace(old_images, config.IMAGES_DIR)
            raise
