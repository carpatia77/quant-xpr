"""
data_fetcher.py
---------------
Fonte de dados de mercado — prioridade:
  1. Arquivo OHLCV local  /tmp/quant_uploads/{TICKER}_ohlcv.csv  (upload manual)
  2. Brapi (brapi.dev)                                            (fallback API)

Funcoes exportadas:
  fetch_ticker_data(ticker, years)  -> pd.DataFrame OHLCV (para Markov)
  fetch_quote(ticker)               -> dict com price, change_percent, company_name
  fetch_multiple_quotes(tickers)    -> dict[ticker, dict] (para watchlist/summary)
"""
import os
import time
import requests
import pandas as pd
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)
BRAPI_BASE  = "https://brapi.dev/api"
_TIMEOUT    = 12
_QUOTE_CACHE: dict = {}
_QUOTE_TTL  = 60
UPLOAD_DIR  = os.environ.get("UPLOAD_DIR", "/tmp/quant_uploads")


def _clean(ticker: str) -> str:
    return ticker.replace(".SA", "").upper()


def _ohlcv_path(ticker: str) -> str:
    return os.path.join(UPLOAD_DIR, f"{_clean(ticker)}_ohlcv.csv")


def _load_ohlcv_from_file(ticker: str) -> pd.DataFrame | None:
    """Lê histórico OHLCV do arquivo de upload manual."""
    path = _ohlcv_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date", "Close"]).set_index("Date").sort_index()
        if df.empty:
            return None
        logger.info("ohlcv_from_file", ticker=_clean(ticker), rows=len(df))
        return df
    except Exception as exc:
        logger.warning("ohlcv_file_read_error", ticker=ticker, error=str(exc))
        return None


def fetch_ticker_data(ticker: str, years: int = 1) -> pd.DataFrame:
    """
    1. Tenta arquivo local (upload manual)
    2. Fallback: Brapi API
    """
    # 1. Arquivo local
    df = _load_ohlcv_from_file(ticker)
    if df is not None:
        return df

    # 2. Brapi
    clean = _clean(ticker)
    last_error = None
    for rng in ["1y", "3mo"]:
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
            df = df[[c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]]
            df = df.dropna(subset=["Close"])
            if df.empty:
                raise ValueError("DataFrame vazio")
            logger.info("brapi_historical_ok", ticker=clean, range=rng, rows=len(df))
            return df
        except Exception as exc:
            logger.warning("brapi_historical_failed", ticker=clean, range=rng, error=str(exc))
            last_error = exc
            time.sleep(0.5)

    raise RuntimeError(f"Sem dados para {ticker}. Faça upload do OHLCV via /v1/upload/ohlcv/{ticker}. Erro Brapi: {last_error}")


def fetch_quote(ticker: str) -> dict:
    """Cotação atual via Brapi. Cache de 1 min."""
    clean = _clean(ticker)
    cached = _QUOTE_CACHE.get(clean)
    if cached and (time.time() - cached["ts"]) < _QUOTE_TTL:
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
            "company_name":   r.get("longName") or r.get("shortName") or ticker,
            "price":          r.get("regularMarketPrice", 0.0),
            "change_percent": r.get("regularMarketChangePercent", 0.0),
            "market_cap":     r.get("marketCap", 0.0),
        }
        _QUOTE_CACHE[clean] = {"data": data, "ts": time.time()}
        return data
    except Exception as exc:
        logger.warning("brapi_quote_failed", ticker=clean, error=str(exc))
        return {}


def fetch_multiple_quotes(tickers: list[str]) -> dict:
    """Cotações em batch via Brapi."""
    if not tickers:
        return {}
    clean_tickers = [_clean(t) for t in tickers]
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
                    "company_name":   r.get("longName") or r.get("shortName") or sym,
                    "price":          r.get("regularMarketPrice", 0.0),
                    "change_percent": r.get("regularMarketChangePercent", 0.0),
                    "market_cap":     r.get("marketCap", 0.0),
                }
        return out
    except Exception as exc:
        logger.warning("brapi_multiple_quotes_failed", error=str(exc))
        return {}
