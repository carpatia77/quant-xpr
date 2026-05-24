"""
run_vol.py
----------
Extrator de superfície de volatilidade via yfinance (cadeia de opções).

IMPORTANTE: yfinance é usado APENAS para opções (tk.option_chain).
O preço spot é sempre derivado do DataFrame histórico (df) passado pelo
cross_analysis — que agora vem da Brapi via data_fetcher.py.

Se df for None ou vazio, retorna {"error": "no_price_data"} sem tentar
buscar nada do yfinance.history (que era a fonte dos timeouts).
"""
import yfinance as yf
import pandas as pd
import argparse
import math
import time
import sys
import structlog
import concurrent.futures
from datetime import datetime

logger = structlog.get_logger(__name__)

_vol_cache: dict = {}
_VOL_CACHE_TTL = 300  # 5 minutos


def _get_vol_surface_impl(ticker_symbol: str, risk_free_rate: float = 0.0, df: pd.DataFrame = None):
    # --- Preço spot: vem obrigatoriamente do df (Brapi) ---
    if df is None or df.empty:
        return {"error": "no_price_data"}

    try:
        current_price = float(df["Close"].iloc[-1])
    except Exception as exc:
        return {"error": f"close_price_error: {exc}"}

    # --- Cadeia de opções: yfinance (única dependência restante) ---
    try:
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
        puts = chain.puts.copy()

        # Forward price ajustado pela taxa livre de risco
        expiry_date = datetime.strptime(nearest_expiry, "%Y-%m-%d")
        days_to_expiry = max((expiry_date - datetime.now()).days, 1)
        T = days_to_expiry / 365.0
        forward_price = current_price * math.exp(risk_free_rate * T)

        # ATM: strike mais próximo do forward
        calls["abs_diff"] = (calls["strike"] - forward_price).abs()
        puts["abs_diff"] = (puts["strike"] - forward_price).abs()
        atm_call = calls.loc[calls["abs_diff"].idxmin()]
        atm_put = puts.loc[puts["abs_diff"].idxmin()]
        atm_iv = (atm_call["impliedVolatility"] + atm_put["impliedVolatility"]) / 2

        # OTM ~10% sobre o forward
        otm_call = calls.iloc[(calls["strike"] - forward_price * 1.10).abs().argsort()[:1]].iloc[0]
        otm_put  = puts.iloc[(puts["strike"]  - forward_price * 0.90).abs().argsort()[:1]].iloc[0]

        skew = otm_put["impliedVolatility"] - otm_call["impliedVolatility"]
        if pd.isna(skew):
            logger.warning("vol_skew_nan", ticker=ticker_symbol)
            skew = 0.0

        # Term structure — 1 vencimento
        vol_term_structure = []
        for exp in expirations[:1]:
            try:
                tc = tk.option_chain(exp)
                tc_calls = tc.calls.copy()
                tc_puts  = tc.puts.copy()
                exp_date = datetime.strptime(exp, "%Y-%m-%d")
                exp_T = max((exp_date - datetime.now()).days, 1) / 365.0
                tfwd = current_price * math.exp(risk_free_rate * exp_T)
                tc_calls["abs_diff"] = (tc_calls["strike"] - tfwd).abs()
                tc_puts["abs_diff"]  = (tc_puts["strike"]  - tfwd).abs()
                term_iv = (
                    tc_calls.loc[tc_calls["abs_diff"].idxmin()]["impliedVolatility"]
                    + tc_puts.loc[tc_puts["abs_diff"].idxmin()]["impliedVolatility"]
                ) / 2
                vol_term_structure.append({"expiry": exp, "atm_iv": term_iv})
            except Exception as exc:
                logger.warning("vol_term_error", ticker=ticker_symbol, expiry=exp, error=str(exc))

        smile_data = (
            calls[["strike", "impliedVolatility"]]
            .rename(columns={"impliedVolatility": "iv"})
            .dropna()
            .to_dict("records")
        )

        return {
            "ticker": ticker_symbol,
            "spot_price": current_price,
            "expiry": nearest_expiry,
            "atm_iv": atm_iv,
            "otm_put_iv": float(otm_put["impliedVolatility"]),
            "otm_call_iv": float(otm_call["impliedVolatility"]),
            "skew": skew,
            "smile_data": smile_data,
            "vol_term_structure": vol_term_structure,
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
        result = future.result(timeout=10.0)
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
    # CLI usa yfinance para histórico apenas para teste local
    try:
        import yfinance as yf
        tk = yf.Ticker(args.ticker)
        df_hist = tk.history(period="5d")
        if df_hist.empty:
            print("Sem dados históricos via yfinance CLI.")
            sys.exit(1)
    except Exception as exc:
        print(f"Erro ao buscar histórico para CLI: {exc}")
        sys.exit(1)

    res = get_vol_surface(args.ticker, df=df_hist)

    if "error" in res:
        print(f"Erro: {res['error']}")
        sys.exit(1)

    print(f"\n--- RELATÓRIO DE VOLATILIDADE: {res['ticker']} ---")
    print(f"Vencimento mais próximo : {res['expiry']}")
    print(f"Preço Spot (Brapi/hist) : R$ {res['spot_price']:.2f}")
    print(f"Volatilidade ATM Média  : {res['atm_iv']*100:.2f}%")
    print(f"Skew (Put OTM - Call OTM): {res['skew']*100:.2f}%")
    if res["skew"] > 0:
        print(">> Mercado precificando MAIOR RISCO DE QUEDA (puts > calls).")
    else:
        print(">> Mercado precificando MAIOR RISCO DE ALTA (calls > puts).")


if __name__ == "__main__":
    main()
