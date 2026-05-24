"""
data_fetcher.py
---------------
Fonte unica de dados de mercado: Brapi (brapi.dev).

Funcoes exportadas:
  fetch_ticker_data(ticker, years)  -> pd.DataFrame OHLCV (para Markov)
  fetch_quote(ticker)               -> dict com price, change_percent, company_name
  fetch_multiple_quotes(tickers)    -> dict[ticker, dict] (para watchlist/summary)
"""
import time
import requests
import pandas as pd
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)
BRAPI_BASE = "https://brapi.dev/api"
_TIMEOUT = 12
_QUOTE_CACHE: dict = {}
_QUOTE_CACHE_TTL = 60  # 1 minuto para quotes


def _clean(ticker: str) -> str:
    return ticker.replace(".SA", "").upper()


def fetch_ticker_data(ticker: str, years: int = 1) -> pd.DataFrame:
    """
    Historico OHLCV via Brapi. Free tier: max range=1y.
    """
    clean = _clean(ticker)
    ranges = ["1y", "3mo"]
    last_error = None

    for rng in ranges:
        try:
            url = f"{BRAPI_BASE}/quote/{clean}"
            params = {
                "range": rng,
                "interval": "1d",
                "fundamental": "false",
                "token": settings.BRAPI_TOKEN,
            }
            resp = requests.get(url, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()

            results = payload.get("results", [])
            if not results:
                raise ValueError(f"Brapi results vazio para {clean} ({rng})")

            historical = results[0].get("historicalDataPrice", [])
            if not historical:
                raise ValueError(f"Brapi sem historicalDataPrice para {clean} ({rng})")

            df = pd.DataFrame(historical)
            df["date"] = pd.to_datetime(df["date"], unit="s", utc=True)
            df = df.set_index("date").sort_index()
            df = df.rename(columns={
                "open": "Open", "high": "High", "low": "Low",
                "close": "Close", "volume": "Volume", "adjustedClose": "Adj Close",
            })
            needed = ["Open", "High", "Low", "Close", "Volume"]
            df = df[[c for c in needed if c in df.columns]].dropna(subset=["Close"])

            if df.empty:
                raise ValueError(f"DataFrame vazio apos normalizacao para {clean}")

            logger.info("brapi_historical_ok", ticker=clean, range=rng, rows=len(df))
            return df

        except Exception as exc:
            logger.warning("brapi_historical_failed", ticker=clean, range=rng, error=str(exc))
            last_error = exc
            time.sleep(0.5)

    raise RuntimeError(f"Brapi historico falhou para {ticker}. Ultimo erro: {last_error}")


def fetch_quote(ticker: str) -> dict:
    """
    Cotacao atual via Brapi: price, change_percent, company_name, market_cap.
    Cache de 1 minuto.
    """
    clean = _clean(ticker)
    cached = _QUOTE_CACHE.get(clean)
    if cached and (time.time() - cached["ts"]) < _QUOTE_CACHE_TTL:
        return cached["data"]

    try:
        url = f"{BRAPI_BASE}/quote/{clean}"
        params = {"token": settings.BRAPI_TOKEN, "fundamental": "false"}
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("results", [])
        if not results:
            return {}
        r = results[0]
        data = {
            "company_name": r.get("longName") or r.get("shortName") or ticker,
            "price": r.get("regularMarketPrice", 0.0),
            "change_percent": r.get("regularMarketChangePercent", 0.0),
            "market_cap": r.get("marketCap", 0.0),
        }
        _QUOTE_CACHE[clean] = {"data": data, "ts": time.time()}
        return data
    except Exception as exc:
        logger.warning("brapi_quote_failed", ticker=clean, error=str(exc))
        return {}


def fetch_multiple_quotes(tickers: list[str]) -> dict:
    """
    Cotacoes em batch via Brapi (ate 10 tickers por request).
    Retorna dict keyed pelo ticker limpo (sem .SA).
    """
    if not tickers:
        return {}

    clean_tickers = [_clean(t) for t in tickers]
    # Brapi aceita multiplos tickers separados por virgula
    symbols = ",".join(clean_tickers)

    try:
        url = f"{BRAPI_BASE}/quote/{symbols}"
        params = {"token": settings.BRAPI_TOKEN, "fundamental": "false"}
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("results", [])
        out = {}
        for r in results:
            sym = r.get("symbol", "").replace(".SA", "")
            if sym:
                out[sym] = {
                    "company_name": r.get("longName") or r.get("shortName") or sym,
                    "price": r.get("regularMarketPrice", 0.0),
                    "change_percent": r.get("regularMarketChangePercent", 0.0),
                    "market_cap": r.get("marketCap", 0.0),
                }
        return out
    except Exception as exc:
        logger.warning("brapi_multiple_quotes_failed", error=str(exc))
        return {}
