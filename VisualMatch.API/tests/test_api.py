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
    embedding = body["images"][0]["embedding"]
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
