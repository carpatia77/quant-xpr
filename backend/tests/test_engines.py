import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from app.services.data_fetcher import fetch_ticker_data
from app.engines.markov_hedge_fund_method.regime import label_regimes, build_transition_matrix, stationary_distribution
from app.engines.run_vol import get_vol_surface

@pytest.mark.slow
def test_data_fetcher_real_qqq():
    # Test if we can successfully pull 1 year of real data for QQQ
    df = fetch_ticker_data("QQQ", years=1)
    assert not df.empty, "Dataframe should not be empty"
    assert "Close" in df.columns, "Dataframe must contain 'Close' prices"
    assert len(df) > 200, "1 year of daily trading data should have around 250 rows"

@pytest.mark.slow
def test_markov_engine_math():
    # Fetch real data for Markov testing using AAPL to spread yfinance rate limits
    df = fetch_ticker_data("AAPL", years=5)
    close = df["Close"].dropna()
    
    # Run the engine steps
    labels = label_regimes(close, window=20, threshold=0.02)
    P = build_transition_matrix(labels)
    pi = stationary_distribution(P)
    
    # Assert Math Properties of Markov Matrices
    assert P.shape == (3, 3), "Transition matrix must be 3x3 for Bear/Neutral/Bull"
    
    # Rows of a transition matrix must sum to 1
    for i in range(3):
        assert np.isclose(np.sum(P[i, :]), 1.0), f"Row {i} of P does not sum to 1"
        
    # Stationary distribution must sum to 1
    assert np.isclose(np.sum(pi), 1.0), "Stationary distribution pi does not sum to 1"

@pytest.mark.slow
def test_vol_surface_real_msft():
    # Fetch real options chain for MSFT
    vol_data = get_vol_surface("MSFT")
    
    # Either returns a valid dictionary with metrics, or an error dictionary if expiration fails
    if "error" not in vol_data:
        assert "atm_iv" in vol_data
        assert "skew" in vol_data
        assert "smile_data" in vol_data
        
        # Smile data must contain data points mapping strike to impliedVolatility
        if len(vol_data["smile_data"]) > 0:
            sample = vol_data["smile_data"][0]
            assert "strike" in sample
            assert "impliedVolatility" in sample
    else:
        # If there's an error due to yfinance limits or missing chains, it should be captured cleanly
        assert isinstance(vol_data["error"], str)

# ==========================================
# MOCKED UNIT TESTS (FAST)
# ==========================================

def test_markov_engine_mocked_data():
    # Create deterministic fake price data
    # 100 days of oscillating prices
    np.random.seed(42)
    prices = np.cumprod(1 + np.random.normal(0, 0.01, 100)) * 100
    dates = pd.date_range("2020-01-01", periods=100)
    close = pd.Series(prices, index=dates)
    
    labels = label_regimes(close, window=10, threshold=0.01)
    P = build_transition_matrix(labels)
    pi = stationary_distribution(P)
    
    assert P.shape == (3, 3)
    for i in range(3):
        assert np.isclose(np.sum(P[i, :]), 1.0)
    assert np.isclose(np.sum(pi), 1.0)

@patch('app.engines.run_vol.yf.Ticker')
def test_vol_surface_mocked(mock_ticker):
    # Mock yfinance Ticker to return empty options to test fallback logic
    # without hitting the network
    instance = mock_ticker.return_value
    instance.options = ()
    
    vol_data = get_vol_surface("FAKE")
    assert "error" in vol_data
    assert "No options chains found" in vol_data["error"]
