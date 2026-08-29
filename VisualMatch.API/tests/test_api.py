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
