"""
data_fetcher.py
---------------
Fonte única de dados históricos OHLCV: Brapi (brapi.dev).
O yfinance foi removido desta camada. O motor de volatilidade (run_vol.py)
continua usando yfinance apenas para a cadeia de opções, que a Brapi não fornece.

Endpoint utilizado:
  GET https://brapi.dev/api/quote/{ticker}
  Parâmetros: range=10y, interval=1d, token=<BRAPI_TOKEN>

Retorno: pd.DataFrame com colunas Open, High, Low, Close, Volume
         indexado por DatetimeIndex UTC.
"""
import time
import requests
import pandas as pd
from app.core.config import settings

BRAPI_BASE = "https://brapi.dev/api"
_TIMEOUT = 12  # segundos


def _brapi_ticker(ticker: str) -> str:
    """Remove sufixo .SA — Brapi usa apenas o código limpo (ex: PETR4)."""
    return ticker.replace(".SA", "").upper()


def fetch_ticker_data(ticker: str, years: int = 10) -> pd.DataFrame:
    """
    Busca histórico OHLCV via Brapi.
    Tenta range=10y primeiro; em caso de falha tenta range=5y.
    Lança RuntimeError se ambas as tentativas falharem.
    """
    clean = _brapi_ticker(ticker)
    ranges = ["10y", "5y"] if years >= 5 else ["1y"]

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
                raise ValueError(f"Brapi retornou results vazio para {clean}")

            historical = results[0].get("historicalDataPrice", [])
            if not historical:
                raise ValueError(f"Brapi sem historicalDataPrice para {clean} range={rng}")

            df = pd.DataFrame(historical)
            # Brapi retorna epoch em segundos na coluna 'date'
            df["date"] = pd.to_datetime(df["date"], unit="s", utc=True)
            df = df.set_index("date").sort_index()

            # Padroniza nomes de colunas para Open/High/Low/Close/Volume
            rename_map = {
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
                "adjustedClose": "Adj Close",
            }
            df = df.rename(columns=rename_map)
            needed = ["Open", "High", "Low", "Close", "Volume"]
            df = df[[c for c in needed if c in df.columns]].dropna(subset=["Close"])

            if df.empty:
                raise ValueError(f"DataFrame vazio após normalização para {clean}")

            return df

        except Exception as exc:
            last_error = exc
            time.sleep(1)

    raise RuntimeError(
        f"Brapi falhou para {ticker} após todas as tentativas. Último erro: {last_error}"
    )
