import pytest
import numpy as np
import pandas as pd

@pytest.fixture
def mock_10y_close_data():
    """Gera uma série temporal determinística de 10 anos (aprox. 2520 pregões) 
    simulando preços de fechamento usando Geometric Brownian Motion."""
    np.random.seed(42)
    # 10 years * 252 trading days = 2520 days
    days = 2520
    # Drift 5% ao ano, Volatilidade 20% ao ano
    mu = 0.05 / 252
    sigma = 0.20 / np.sqrt(252)
    
    returns = np.random.normal(mu, sigma, days)
    # Preço inicial = 100
    prices = 100 * np.exp(np.cumsum(returns))
    
    dates = pd.date_range(end=pd.Timestamp.now().normalize(), periods=days, freq='B')
    return pd.Series(prices, index=dates, name="Close")
