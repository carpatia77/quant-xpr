import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_unauthorized_access():
    response = client.get(f"{settings.API_V1_STR}/assets")
    assert response.status_code == 403
    assert response.json() == {"detail": "Could not validate API KEY"}

def test_authorized_access_assets():
    headers = {"X-API-Key": settings.API_KEY}
    response = client.get(f"{settings.API_V1_STR}/assets", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
