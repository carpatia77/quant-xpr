"""
run_vol.py
----------
Extrator de superfície de volatilidade.

Fonte de dados (prioridade):
  1. Arquivo local /tmp/quant_uploads/{TICKER}_options.csv  (upload manual B3)
  2. yfinance option_chain                                  (fallback API)

O preço spot sempre vem do df (Brapi/OHLCV manual) passado pelo cross_analysis.
"""
import os
import math
import time
import sys
import argparse
import concurrent.futures
from datetime import datetime

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

_vol_cache: dict = {}
_VOL_CACHE_TTL = 300  # 5 minutos
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/quant_uploads")


def _options_path(ticker: str) -> str:
    clean = ticker.upper().replace(".SA", "")
    return os.path.join(UPLOAD_DIR, f"{clean}_options.csv")


def _load_options_from_file(ticker: str, current_price: float, risk_free_rate: float) -> dict:
    """
    Lê grade de opções do arquivo CSV (upload manual via /v1/upload/options).
    Calcula IV ATM, skew e smile sem depender de yfinance.
    """
    path = _options_path(ticker)
    if not os.path.exists(path):
        return None  # sinaliza: usar fallback yfinance

    try:
        df = pd.read_csv(path)
        df.columns = [str(c).strip().lower() for c in df.columns]

        if "iv" not in df.columns or "strike" not in df.columns:
            logger.warning("options_file_missing_cols", ticker=ticker, cols=list(df.columns))
            return None

        df["iv"]     = pd.to_numeric(df["iv"],     errors="coerce")
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
        df = df.dropna(subset=["iv", "strike"])

        # Normaliza IV se veio em % (ex: 35.1 em vez de 0.351)
        if df["iv"].mean() > 2.0:
            df["iv"] = df["iv"] / 100.0

        # Separa calls e puts
        if "type" in df.columns:
            calls = df[df["type"].str.upper() == "CALL"].copy()
            puts  = df[df["type"].str.upper() == "PUT"].copy()
        else:
            calls = df.copy()
            puts  = df.copy()

        # ATM: strike mais próximo do forward price
        expiry_str = df["expiry_date"].dropna().iloc[0] if "expiry_date" in df.columns and not df["expiry_date"].dropna().empty else None
        T = 30 / 365.0  # fallback 30 dias
        if expiry_str:
            try:
                exp_date = pd.to_datetime(expiry_str)
                days = max((exp_date - pd.Timestamp.now()).days, 1)
                T = days / 365.0
            except Exception:
                pass

        forward = current_price * math.exp(risk_free_rate * T)

        calls["dist"] = (calls["strike"] - forward).abs()
        puts["dist"]  = (puts["strike"]  - forward).abs()

        atm_call_iv = calls.loc[calls["dist"].idxmin(), "iv"] if not calls.empty else None
        atm_put_iv  = puts.loc[puts["dist"].idxmin(),  "iv"] if not puts.empty  else None

        if atm_call_iv is not None and atm_put_iv is not None:
            atm_iv = (atm_call_iv + atm_put_iv) / 2
        elif atm_call_iv is not None:
            atm_iv = atm_call_iv
        elif atm_put_iv is not None:
            atm_iv = atm_put_iv
        else:
            atm_iv = df["iv"].mean()

        # Skew: put OTM - call OTM
        otm_calls = calls[calls["strike"] > forward * 1.05]
        otm_puts  = puts[puts["strike"]  < forward * 0.95]
        otm_call_iv_avg = otm_calls["iv"].mean() if not otm_calls.empty else atm_iv
        otm_put_iv_avg  = otm_puts["iv"].mean()  if not otm_puts.empty  else atm_iv
        skew = otm_put_iv_avg - otm_call_iv_avg
        if pd.isna(skew):
            skew = 0.0

        # Smile: todos os strikes de calls ordenados
        smile_data = (
            calls[["strike", "iv"]]
            .dropna()
            .sort_values("strike")
            .rename(columns={"iv": "iv"})
            .to_dict("records")
        )

        # Term structure (único vencimento disponível)
        expiry_label = str(expiry_str) if expiry_str else "manual"
        vol_term_structure = [{"expiry": expiry_label, "atm_iv": float(atm_iv)}]

        logger.info("vol_from_file", ticker=ticker, atm_iv=round(atm_iv, 4), skew=round(skew, 4), rows=len(df))

        return {
            "ticker": ticker,
            "spot_price": current_price,
            "expiry": expiry_label,
            "atm_iv": float(atm_iv),
            "otm_put_iv": float(otm_put_iv_avg),
            "otm_call_iv": float(otm_call_iv_avg),
            "skew": float(skew),
            "smile_data": smile_data,
            "vol_term_structure": vol_term_structure,
            "source": "manual_upload",
        }

    except Exception as exc:
        logger.error("options_file_read_error", ticker=ticker, error=str(exc))
        return None


def _get_vol_surface_impl(ticker_symbol: str, risk_free_rate: float = 0.0, df: pd.DataFrame = None):
    # Spot price sempre vem do df (Brapi ou OHLCV manual)
    if df is None or df.empty:
        return {"error": "no_price_data"}

    try:
        current_price = float(df["Close"].iloc[-1])
    except Exception as exc:
        return {"error": f"close_price_error: {exc}"}

    # 1. Tenta arquivo de opções manual (upload B3)
    file_result = _load_options_from_file(ticker_symbol, current_price, risk_free_rate)
    if file_result is not None:
        return file_result

    # 2. Fallback: yfinance option_chain
    logger.info("vol_fallback_yfinance", ticker=ticker_symbol)
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker_symbol)
        expirations = tk.options
    except Exception as exc:
        return {"error": f"options_fetch_error: {exc}"}

    if not expirations:
        return {"error": "no_options_chain"}

    try:
        nearest_expiry = expirations[0]
        chain = tk.option_chain(nearest_expiry)
        calls = chain.calls.copy()
        puts  = chain.puts.copy()

        expiry_date = datetime.strptime(nearest_expiry, "%Y-%m-%d")
        days_to_expiry = max((expiry_date - datetime.now()).days, 1)
        T = days_to_expiry / 365.0
        forward_price = current_price * math.exp(risk_free_rate * T)

        calls["abs_diff"] = (calls["strike"] - forward_price).abs()
        puts["abs_diff"]  = (puts["strike"]  - forward_price).abs()
        atm_call = calls.loc[calls["abs_diff"].idxmin()]
        atm_put  = puts.loc[puts["abs_diff"].idxmin()]
        atm_iv   = (atm_call["impliedVolatility"] + atm_put["impliedVolatility"]) / 2

        otm_call = calls.iloc[(calls["strike"] - forward_price * 1.10).abs().argsort()[:1]].iloc[0]
        otm_put  = puts.iloc[(puts["strike"]   - forward_price * 0.90).abs().argsort()[:1]].iloc[0]
        skew = otm_put["impliedVolatility"] - otm_call["impliedVolatility"]
        if pd.isna(skew):
            skew = 0.0

        smile_data = (
            calls[["strike", "impliedVolatility"]]
            .rename(columns={"impliedVolatility": "iv"})
            .dropna()
            .to_dict("records")
        )

        vol_term_structure = [{"expiry": nearest_expiry, "atm_iv": float(atm_iv)}]

        return {
            "ticker": ticker_symbol,
            "spot_price": current_price,
            "expiry": nearest_expiry,
            "atm_iv": float(atm_iv),
            "otm_put_iv": float(otm_put["impliedVolatility"]),
            "otm_call_iv": float(otm_call["impliedVolatility"]),
            "skew": float(skew),
            "smile_data": smile_data,
            "vol_term_structure": vol_term_structure,
            "source": "yfinance",
        }
    except Exception as exc:
        return {"error": str(exc)}


def get_vol_surface(ticker_symbol: str, risk_free_rate: float = 0.0, df: pd.DataFrame = None):
    cache_key = f"{ticker_symbol}:{round(risk_free_rate, 4)}"
    cached = _vol_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _VOL_CACHE_TTL:
        return cached["data"]

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_get_vol_surface_impl, ticker_symbol, risk_free_rate, df)
    try:
        result = future.result(timeout=15.0)
        if "error" not in result:
            _vol_cache[cache_key] = {"data": result, "ts": time.time()}
        return result
    except concurrent.futures.TimeoutError:
        logger.warning("vol_surface_timeout", ticker=ticker_symbol)
        return {"error": "timeout"}
    finally:
        executor.shutdown(wait=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="PETR4.SA")
    args = parser.parse_args()
    print(f"Buscando superfície de volatilidade para {args.ticker}...")
    try:
        import yfinance as yf
        tk = yf.Ticker(args.ticker)
        df_hist = tk.history(period="5d")
        if df_hist.empty:
            print("Sem dados históricos via yfinance CLI.")
            sys.exit(1)
    except Exception as exc:
        print(f"Erro: {exc}")
        sys.exit(1)
    res = get_vol_surface(args.ticker, df=df_hist)
    if "error" in res:
        print(f"Erro: {res['error']}")
        sys.exit(1)
    print(f"ATM IV : {res['atm_iv']*100:.2f}%")
    print(f"Skew   : {res['skew']*100:.2f}%")
    print(f"Fonte  : {res.get('source','?')}")


if __name__ == "__main__":
    main()
