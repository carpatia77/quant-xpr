import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.1.0"}

def test_unauthorized_access():
    response = client.get(f"{settings.API_V1_STR}/assets")
    assert response.status_code == 403
    assert response.json() == {"detail": "Could not validate API KEY"}

def test_authorized_access_assets():
    headers = {"X-API-Key": settings.API_KEY}
    response = client.get(f"{settings.API_V1_STR}/assets", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.slow
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

@patch('app.api.v1.endpoints.run_cross_analysis')
def test_summary_mocked_endpoint(mock_run_cross_analysis):
    headers = {"X-API-Key": settings.API_KEY}
    
    # Mock the return value of the heavily computational function
    mock_run_cross_analysis.return_value = {
        "ticker": "MOCK_TICKER",
        "markov_bull_prob": 0.85,
        "markov_bear_prob": 0.05,
        "iv_atm": 0.20,
        "skew": 0.05,
        "signal": "long_vol",
        "status": "Markov: ok | Vol: ok",
        "smile_data": [],
        "vol_term_structure": [],
        "regime_history": [],
        "risk_free_rate": 0.1325,
        "risk_free_rate_source": "BCB SGS 11 (Selic Over)"
    }
    
    response = client.get(f"{settings.API_V1_STR}/summary/MOCK_TICKER", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "MOCK_TICKER"
    assert data["signal"] == "long_vol"
    assert data["markov_bull_prob"] == 0.85
    
    # Verify DB persistence of the mock
    response_history = client.get(f"{settings.API_V1_STR}/history/MOCK_TICKER", headers=headers)
    assert response_history.status_code == 200
    history_data = response_history.json()
    assert len(history_data) > 0
    assert history_data[0]["ticker"] == "MOCK_TICKER"
    assert history_data[0]["signal"] == "long_vol"

@patch('app.api.v1.endpoints.run_cross_analysis')
def test_summary_invalid_ticker(mock_run_cross_analysis):
    headers = {"X-API-Key": settings.API_KEY}
    
    mock_run_cross_analysis.return_value = {
        "ticker": "INVALID",
        "markov_bull_prob": 0.0,
        "markov_bear_prob": 0.0,
        "iv_atm": 0.0,
        "skew": 0.0,
        "signal": "error_fetching_data",
        "status": "Markov: error | Vol: error",
        "smile_data": [],
        "vol_term_structure": [],
        "regime_history": [],
        "risk_free_rate": 0.0,
        "risk_free_rate_source": "Zero"
    }
    
    response = client.get(f"{settings.API_V1_STR}/summary/INVALID", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["signal"].startswith("error_")

@patch('app.api.v1.endpoints.asyncio.wait_for')
def test_summary_timeout(mock_wait_for):
    import asyncio
    headers = {"X-API-Key": settings.API_KEY}
    
    # Simulate a timeout from asyncio.wait_for
    mock_wait_for.side_effect = asyncio.TimeoutError()
    
    response = client.get(f"{settings.API_V1_STR}/summary/SLOW_TICKER", headers=headers)
    assert response.status_code == 504
    assert response.json()["detail"] == "Engine analysis timed out"

def test_history_ordering():
    headers = {"X-API-Key": settings.API_KEY}
    
    # Use the mocked summary endpoint from earlier to populate some data
    with patch('app.api.v1.endpoints.run_cross_analysis') as mock_run:
        mock_run.return_value = {
            "ticker": "ORDER_TEST",
            "markov_bull_prob": 0.5,
            "markov_bear_prob": 0.5,
            "iv_atm": 0.2,
            "skew": 0.0,
            "signal": "neutral",
            "status": "ok",
            "smile_data": [],
            "vol_term_structure": [],
            "regime_history": [],
            "risk_free_rate": 0.0,
            "risk_free_rate_source": ""
        }
        
        # Call 3 times
        for _ in range(3):
            client.get(f"{settings.API_V1_STR}/summary/ORDER_TEST", headers=headers)
            
    # Fetch history
    response = client.get(f"{settings.API_V1_STR}/history/ORDER_TEST", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 3
    
    # Check if ordered by timestamp DESC
    timestamps = [item["timestamp"] for item in data]
    # To check if sorted DESC, sorted(timestamps, reverse=True) should equal timestamps
    assert timestamps == sorted(timestamps, reverse=True), "History is not ordered by timestamp DESC"
