import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

def fetch_stock_quote(ticker: str) -> dict:
    """
    Fetches broad stock fundamental data from HG Brasil Free API.
    Provides company name, current price, variation, market cap, etc.
    """
    if not settings.HG_BRASIL_API_KEY:
        logger.warning("hg_brasil_api_key_missing", msg="HG_BRASIL_API_KEY is not configured, skipping broad data fetch.")
        return {}

    # For HG Brasil, B3 tickers usually don't need the .SA suffix, or they can take it.
    # HG Brasil accepts 'PETR4' or 'B3:PETR4'. If it has .SA, we might want to strip it.
    clean_ticker = ticker.replace('.SA', '')

    url = "https://api.hgbrasil.com/finance/stock_price"
    params = {
        "key": settings.HG_BRASIL_API_KEY,
        "symbol": clean_ticker
    }

    try:
        # 8-second timeout, same as the others
        with httpx.Client(timeout=8.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        # Check if the API returned valid data
        if not data.get("valid_key"):
            logger.error("hg_brasil_invalid_key", error=data.get("errors", "Unknown key error"))
            return {}

        results = data.get("results", {})
        
        # HG Brasil returns a dictionary where the ticker is the key: {"PETR4": {"name": ...}}
        ticker_data = results.get(clean_ticker.upper(), {})
        
        # In case it returned an error object inside results (e.g., symbol not found)
        if ticker_data.get("error"):
            logger.warning("hg_brasil_symbol_error", ticker=ticker, msg=ticker_data.get("message"))
            return {}

        return {
            "company_name": ticker_data.get("company_name", ticker_data.get("name", "")),
            "price": ticker_data.get("price", 0.0),
            "change_percent": ticker_data.get("change_percent", 0.0),
            "market_cap": ticker_data.get("market_cap", 0.0)
        }

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

    # Clean and format tickers for HG Brasil (e.g., 'PETR4' instead of 'PETR4.SA')
    # and prefix with 'B3:' if they are Brazilian stocks, though HG Brasil often accepts just the symbol.
    clean_tickers = [t.replace('.SA', '') for t in tickers]
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

        return parsed_results

    except Exception as exc:
        logger.warning("hg_brasil_multiple_fetch_error", error=str(exc))
        return {}
