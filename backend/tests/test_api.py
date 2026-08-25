import os

os.environ["ADMIN_USERNAME"] = "ExpertKF"
os.environ["ADMIN_PASSWORD_HASH"] = "dummy-hash-for-tests"
os.environ["API_ALLOWED_ORIGIN"] = "http://localhost:3000"
os.environ["TOKEN_TTL_SECONDS"] = "3600"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"


def test_sources():
    response = client.get("/api/sources")
    assert response.status_code == 200

    data = response.json()
    assert "sources" in data
    assert len(data["sources"]) > 0


def test_analyze_requires_auth():
    response = client.post(
        "/api/analyze",
        json={
            "context": "Litige avec vendeur professionnel concernant un vice caché sur moteur.",
            "actor": "vendeur_professionnel"
        }
    )

    assert response.status_code == 401


def test_access_request():
    response = client.post(
        "/api/access/request",
        json={
            "device_id": "test-device",
            "contact": "test@example.com",
            "message": "Demande de test"
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
