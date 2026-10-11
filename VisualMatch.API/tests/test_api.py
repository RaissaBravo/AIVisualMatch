import io
import zipfile

import numpy as np


def test_product_crud(client):
    created = client.post("/api/products", data={"name": "Colchão Modelo A"})
    assert created.status_code == 201
    product_id = created.json()["id"]
    listed = client.get("/api/products").json()
    assert listed == [{"id": product_id, "name": "Colchão Modelo A", "embeddings": []}]
    updated = client.put(f"/api/products/{product_id}", data={"name": "Modelo A Plus"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Modelo A Plus"
    assert client.delete(f"/api/products/{product_id}").status_code == 204
    assert client.get(f"/api/products/{product_id}").status_code == 404


def test_upload_store_and_delete_image(client, jpeg_bytes):
    created = client.post("/api/products", data={"name": "Produto"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))])
    assert created.status_code == 201, created.text
    body = created.json()
    assert set(body["images"][0]["embeddings"]) == {"fake", "fake-b"}
    embedding = body["images"][0]["embeddings"]["fake"]
    assert len(embedding) == 4
    assert np.isclose(np.linalg.norm(embedding), 1.0)
    image_id = body["images"][0]["id"]
    listing = client.get("/api/products").json()
    assert listing[0]["embeddings"] == [embedding]
    response = client.delete(f"/api/products/{body['id']}/images/{image_id}")
    assert response.status_code == 204
    assert client.get(f"/api/products/{body['id']}").json()["images"] == []


def test_invalid_image_is_rejected_without_product(client):
    response = client.post("/api/products", data={"name": "Inválido"}, files=[("images", ("fake.jpg", b"not-image", "image/jpeg"))])
    assert response.status_code == 422
    assert client.get("/api/products").json() == []


def test_admin_backup_and_restore_round_trip(client, jpeg_bytes):
    created = client.post(
        "/api/products",
        data={"name": "Produto original"},
        files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))],
    ).json()

    downloaded = client.get("/admin/backup")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
        names = archive.namelist()
        assert "data/products.db" in names
        assert any(name.startswith(f"images/{created['id']}/") for name in names)

    assert client.delete(f"/api/products/{created['id']}").status_code == 204
    assert client.get("/api/products").json() == []

    restored = client.post(
        "/admin/restore",
        files={"backup": ("visualmatch-backup.zip", downloaded.content, "application/zip")},
        follow_redirects=False,
    )
    assert restored.status_code == 303
    products = client.get("/api/products").json()
    assert products[0]["id"] == created["id"]
    assert products[0]["name"] == "Produto original"
    detail = client.get(f"/api/products/{created['id']}").json()
    restored_backup = client.get("/admin/backup")
    with zipfile.ZipFile(io.BytesIO(restored_backup.content)) as archive:
        image_name = detail["images"][0]["url"].lstrip("/")
        assert archive.read(image_name) == jpeg_bytes


def test_admin_restore_rejects_zip_outside_expected_structure(client):
    client.post("/api/products", data={"name": "Deve permanecer"})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../products.db", b"invalid")

    response = client.post(
        "/admin/restore",
        files={"backup": ("backup.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 422
    assert "caminho inválido" in response.text
    assert client.get("/api/products").json()[0]["name"] == "Deve permanecer"


def test_products_are_listed_per_model(client, jpeg_bytes):
    created = client.post("/api/products", data={"name": "Produto"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))]).json()
    default = client.get("/api/products").json()[0]["embeddings"]
    other = client.get("/api/products?model=fake-b").json()[0]["embeddings"]
    assert default == [created["images"][0]["embeddings"]["fake"]]
    assert np.allclose(other[0], default[0][::-1])
    assert client.get("/api/products?model=desconhecido").status_code == 404
    assert client.get("/api/model-info").json()["model"] == "fake"
    assert client.get("/api/model-info?model=fake-b").json()["model"] == "fake-b"


def test_new_model_is_backfilled_without_touching_others(client, jpeg_bytes):
    second = client.app.state.models.services["fake-b"]
    second.available = False
    client.post("/api/products", data={"name": "Produto"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))])
    coverage = {item["model"]: item["embedded_images"] for item in client.get("/api/models").json()}
    assert coverage == {"fake": 1, "fake-b": 0}
    assert client.get("/api/products?model=fake-b").json()[0]["embeddings"] == []

    second.available = True
    response = client.post("/api/regenerate-all-embeddings?model=fake-b")
    assert response.status_code == 200, response.text
    assert response.json() == {"products": 1, "embeddings": 1}
    models = client.get("/api/models").json()
    assert [(m["model"], m["embedded_images"], m["total_images"]) for m in models] == [("fake", 1, 1), ("fake-b", 1, 1)]


def test_model_file_is_served_for_the_app(client, tmp_path):
    service = client.app.state.models.services["fake"]
    service.model_path = tmp_path / "fake.onnx"
    service.model_path.write_bytes(b"onnx-bytes")
    response = client.get("/api/models/fake/file")
    assert response.status_code == 200
    assert response.content == b"onnx-bytes"
    service.available = False
    assert client.get("/api/models/fake/file").status_code == 404
    assert client.get("/api/models/desconhecido/file").status_code == 404


def test_single_model_schema_is_migrated(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    from app.database import upgrade_schema

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(200) NOT NULL, created_at DATETIME, updated_at DATETIME)")
        connection.exec_driver_sql("CREATE TABLE product_images (id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE, file_path VARCHAR(500) NOT NULL, file_name VARCHAR(255) NOT NULL, embedding TEXT NOT NULL, created_at DATETIME)")
        connection.exec_driver_sql("INSERT INTO products VALUES (1, 'Antigo', '2026-01-01', '2026-01-01')")
        connection.exec_driver_sql("INSERT INTO product_images VALUES (7, 1, 'images/1/a.jpg', 'a.jpg', '[0.6,0.8]', '2026-01-01')")
    upgrade_schema(engine)
    upgrade_schema(engine)
    assert "embedding" not in {column["name"] for column in inspect(engine).get_columns("product_images")}
    assert "model_md5" in {column["name"] for column in inspect(engine).get_columns("image_embeddings")}
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT image_id, model_id, embedding FROM image_embeddings")).all()
    assert rows == [(7, "mobilenetv2", "[0.6,0.8]")]


def test_outdated_embeddings_are_not_served_until_regenerated(client, jpeg_bytes):
    client.post("/api/products", data={"name": "Produto"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))])
    client.app.state.models.services["fake-b"].file_md5 = "arquivo-reexportado"
    summary = {item["model"]: item for item in client.get("/api/models").json()}["fake-b"]
    assert (summary["embedded_images"], summary["outdated_images"], summary["missing_images"], summary["pending_images"]) == (0, 1, 0, 1)
    assert client.get("/api/products?model=fake-b").json()[0]["embeddings"] == []

    response = client.post("/admin/models/fake-b/generate", follow_redirects=False)
    assert response.status_code == 303
    assert len(client.get("/api/products?model=fake-b").json()[0]["embeddings"]) == 1
    assert {item["model"]: item["pending_images"] for item in client.get("/api/models").json()} == {"fake": 0, "fake-b": 0}


def test_startup_generates_every_model_embeddings(client, jpeg_bytes):
    from app.main import sync_all_models

    client.post("/api/products", data={"name": "Produto"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))])
    models = client.app.state.models
    for service in models.services.values():
        service.file_md5 = "arquivo-reexportado"
    assert client.get("/api/products?model=fake").json()[0]["embeddings"] == []
    assert client.get("/api/products?model=fake-b").json()[0]["embeddings"] == []
    sync_all_models(models)
    assert len(client.get("/api/products?model=fake").json()[0]["embeddings"]) == 1
    assert len(client.get("/api/products?model=fake-b").json()[0]["embeddings"]) == 1


def test_upload_works_while_a_model_file_is_missing(client, jpeg_bytes):
    client.app.state.models.services["fake-b"].available = False
    created = client.post("/api/products", data={"name": "Produto"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))])
    assert created.status_code == 201, created.text
    assert set(created.json()["images"][0]["embeddings"]) == {"fake"}
    for service in client.app.state.models.services.values():
        service.available = False
    response = client.post("/api/products", data={"name": "Outro"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))])
    assert response.status_code == 503


def test_admin_shows_readiness_of_every_model(client, jpeg_bytes):
    created = client.post("/api/products", data={"name": "Produto"}, files=[("images", ("foto.jpg", jpeg_bytes, "image/jpeg"))]).json()
    page = client.get("/").text
    assert "Todos os 2 modelos prontos" in page
    assert "embeddings em todos os modelos" in page
    client.app.state.models.services["fake-b"].file_md5 = "arquivo-reexportado"
    page = client.get("/").text
    assert "1 de 2 modelos prontos" in page
    assert "Gerar 1 pendentes de FAKE-B" in page
    assert "embeddings pendentes em FAKE-B" in page
    detail = client.get(f"/admin/products/{created['id']}").text
    assert "FAKE: ✓" in detail and "FAKE-B: desatualizado" in detail
