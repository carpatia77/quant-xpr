import httpx
import structlog
import time
from app.core.config import settings

logger = structlog.get_logger(__name__)

# 15 minutes = 900 seconds cache to respect 400 requests/day limit
CACHE_DURATION = 900
_hg_cache_single = {}
_hg_cache_multiple = {}

def fetch_stock_quote(ticker: str) -> dict:
    """
    Fetches broad stock fundamental data from HG Brasil Free API.
    Provides company name, current price, variation, market cap, etc.
    """
    if not settings.HG_BRASIL_API_KEY:
        logger.warning("hg_brasil_api_key_missing", msg="HG_BRASIL_API_KEY is not configured, skipping broad data fetch.")
        return {}

    clean_ticker = ticker.replace('.SA', '')
    
    # Check cache
    if clean_ticker in _hg_cache_single:
        entry = _hg_cache_single[clean_ticker]
        if time.time() - entry["ts"] < CACHE_DURATION:
            return entry["data"]

    url = "https://api.hgbrasil.com/finance/stock_price"
    params = {
        "key": settings.HG_BRASIL_API_KEY,
        "symbol": clean_ticker
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if not data.get("valid_key"):
            logger.error("hg_brasil_invalid_key", error=data.get("errors", "Unknown key error"))
            return {}

        results = data.get("results", {})
        ticker_data = results.get(clean_ticker.upper(), {})
        
        if ticker_data.get("error"):
            logger.warning("hg_brasil_symbol_error", ticker=ticker, msg=ticker_data.get("message"))
            return {}

        final_data = {
            "company_name": ticker_data.get("company_name", ticker_data.get("name", "")),
            "price": ticker_data.get("price", 0.0),
            "change_percent": ticker_data.get("change_percent", 0.0),
            "market_cap": ticker_data.get("market_cap", 0.0)
        }
        
        # Save to cache
        _hg_cache_single[clean_ticker] = {"data": final_data, "ts": time.time()}
        return final_data

    except Exception as exc:
        logger.warning("hg_brasil_fetch_error", ticker=ticker, error=str(exc))
        return {}

def fetch_multiple_stock_quotes(tickers: list[str]) -> dict:
    """
    Fetches broad stock fundamental data for MULTIPLE tickers from HG Brasil Free API.
    Returns a dictionary keyed by the clean ticker (e.g. 'PETR4').
    """
    if not settings.HG_BRASIL_API_KEY or not tickers:
        return {}

    clean_tickers = [t.replace('.SA', '') for t in tickers]
    # Sort so the cache key is deterministic
    cache_key = ",".join(sorted(clean_tickers))
    
    # Check cache
    if cache_key in _hg_cache_multiple:
        entry = _hg_cache_multiple[cache_key]
        if time.time() - entry["ts"] < CACHE_DURATION:
            return entry["data"]

    tickers_str = ",".join(clean_tickers)

    url = "https://api.hgbrasil.com/finance/stock_price"
    params = {
        "key": settings.HG_BRASIL_API_KEY,
        "symbol": tickers_str
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if not data.get("valid_key"):
            return {}

        results = data.get("results", {})
        
        parsed_results = {}
        for ticker in clean_tickers:
            ticker_data = results.get(ticker.upper(), {})
            if ticker_data and not ticker_data.get("error"):
                parsed_results[ticker] = {
                    "company_name": ticker_data.get("company_name", ticker_data.get("name", "")),
                    "price": ticker_data.get("price", 0.0),
                    "change_percent": ticker_data.get("change_percent", 0.0),
                    "market_cap": ticker_data.get("market_cap", 0.0)
                }

        # Save to cache
        _hg_cache_multiple[cache_key] = {"data": parsed_results, "ts": time.time()}
        return parsed_results

    except Exception as exc:
        logger.warning("hg_brasil_multiple_fetch_error", error=str(exc))
        return {}
