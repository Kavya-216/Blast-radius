from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ready"


def test_repository_registration_and_lookup(tmp_path):
    repository_id = "demo-api"
    response = client.post(
        "/repositories",
        json={"repository_id": repository_id, "local_path": str(tmp_path)},
    )
    assert response.status_code == 201
    assert response.json()["repository_id"] == repository_id

    lookup = client.get(f"/repositories/{repository_id}")
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "registered"


def test_missing_repository_returns_404():
    response = client.get("/repositories/does-not-exist")
    assert response.status_code == 404
