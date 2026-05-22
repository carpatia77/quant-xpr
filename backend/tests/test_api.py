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

def test_summary_real_spy_endpoint():
    # This hits yfinance directly in testing via the endpoint
    headers = {"X-API-Key": settings.API_KEY}
    # Using SPY since it is the most liquid and reliable ETF on Yahoo Finance
    response = client.get(f"{settings.API_V1_STR}/summary/SPY", headers=headers)
    
    # 200 OK
    assert response.status_code == 200
    
    data = response.json()
    assert "ticker" in data
    assert data["ticker"] == "SPY"
    assert "markov_bull_prob" in data
    assert "signal" in data
    
    # Check if the DB transaction was successful by requesting history
    response_history = client.get(f"{settings.API_V1_STR}/history/SPY", headers=headers)
    assert response_history.status_code == 200
    history_data = response_history.json()
    assert len(history_data) > 0
    assert history_data[0]["ticker"] == "SPY"
