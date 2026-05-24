"""Volatility Surface and Skew Extractor via yfinance."""
import yfinance as yf
import pandas as pd
import argparse
import math
from datetime import datetime
import sys

import concurrent.futures

def _get_vol_surface_impl(ticker_symbol: str, risk_free_rate: float = 0.0, df: pd.DataFrame = None):
    tk = yf.Ticker(ticker_symbol)
    try:
        if df is not None and not df.empty:
            current_price = df['Close'].iloc[-1]
        else:
            current_price = tk.history(period="1d")['Close'].iloc[-1]
        expirations = tk.options
        if not expirations:
            return {"error": "Nenhuma cadeia de opções encontrada."}
        
        nearest_expiry = expirations[0]
        chain = tk.option_chain(nearest_expiry)
        calls = chain.calls
        puts = chain.puts
        
        # Calculate Forward Price for nearest expiry
        expiry_date = datetime.strptime(nearest_expiry, "%Y-%m-%d")
        days_to_expiry = (expiry_date - datetime.now()).days
        if days_to_expiry <= 0: days_to_expiry = 1
        T = days_to_expiry / 365.0
        forward_price = current_price * math.exp(risk_free_rate * T)
        
        # Filtrar Strikes próximos ao preço forward (ATM)
        calls['abs_diff'] = abs(calls['strike'] - forward_price)
        puts['abs_diff'] = abs(puts['strike'] - forward_price)
        
        atm_call = calls.loc[calls['abs_diff'].idxmin()]
        atm_put = puts.loc[puts['abs_diff'].idxmin()]
        atm_iv = (atm_call['impliedVolatility'] + atm_put['impliedVolatility']) / 2
        
        # Filtrar Strikes OTM (~10% out of the money) sobre o forward
        otm_call_strike = forward_price * 1.10
        otm_put_strike = forward_price * 0.90
        
        otm_call = calls.iloc[(calls['strike'] - otm_call_strike).abs().argsort()[:1]].iloc[0]
        otm_put = puts.iloc[(puts['strike'] - otm_put_strike).abs().argsort()[:1]].iloc[0]
        
        import structlog
        logger = structlog.get_logger(__name__)
        
        skew = otm_put['impliedVolatility'] - otm_call['impliedVolatility']
        if pd.isna(skew):
            logger.warning("vol_surface_skew_nan", ticker=ticker_symbol, msg="Illiquid OTM options caused NaN skew, falling back to 0.0")
            skew = 0.0
        
        # Calculate Volatility Term Structure for up to 3 expirations
        vol_term_structure = []
        for exp in expirations[:3]:
            try:
                term_chain = tk.option_chain(exp)
                term_calls = term_chain.calls
                term_puts = term_chain.puts
                
                exp_date = datetime.strptime(exp, "%Y-%m-%d")
                exp_days = (exp_date - datetime.now()).days
                if exp_days <= 0: exp_days = 1
                exp_T = exp_days / 365.0
                term_forward_price = current_price * math.exp(risk_free_rate * exp_T)
                
                term_calls['abs_diff'] = abs(term_calls['strike'] - term_forward_price)
                term_puts['abs_diff'] = abs(term_puts['strike'] - term_forward_price)
                
                term_atm_call = term_calls.loc[term_calls['abs_diff'].idxmin()]
                term_atm_put = term_puts.loc[term_puts['abs_diff'].idxmin()]
                term_atm_iv = (term_atm_call['impliedVolatility'] + term_atm_put['impliedVolatility']) / 2
                
                vol_term_structure.append({
                    "expiry": exp,
                    "atm_iv": term_atm_iv
                })
            except Exception as exc:
                logger.warning("vol_term_structure_error", ticker=ticker_symbol, expiry=exp, error=str(exc))
        
        # Build smile data from calls for simplicity
        smile_data = calls[['strike', 'impliedVolatility']].rename(columns={'impliedVolatility': 'iv'}).dropna().to_dict('records')
        
        return {
            "ticker": ticker_symbol,
            "spot_price": current_price,
            "expiry": nearest_expiry,
            "atm_iv": atm_iv,
            "otm_put_iv": otm_put['impliedVolatility'],
            "otm_call_iv": otm_call['impliedVolatility'],
            "skew": skew,
            "smile_data": smile_data,
            "vol_term_structure": vol_term_structure
        }
    except Exception as e:
        return {"error": str(e)}

def get_vol_surface(ticker_symbol: str, risk_free_rate: float = 0.0, df: pd.DataFrame = None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_get_vol_surface_impl, ticker_symbol, risk_free_rate, df)
        try:
            return future.result(timeout=8.0)
        except concurrent.futures.TimeoutError:
            import structlog
            logger = structlog.get_logger(__name__)
            logger.warning("vol_surface_timeout", ticker=ticker_symbol, msg="yfinance options fetching timed out after 8s")
            return {"error": "timeout"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="PETR4.SA")
    args = parser.parse_args()
    
    print(f"Buscando superfície de volatilidade para {args.ticker}...")
    res = get_vol_surface(args.ticker)
    
    if "error" in res:
        print(f"Erro: {res['error']}")
        sys.exit(1)
        
    print(f"\n--- RELATÓRIO DE VOLATILIDADE: {res['ticker']} ---")
    print(f"Vencimento mais próximo: {res['expiry']}")
    print(f"Preço Spot Atual: R$ {res['spot_price']:.2f}")
    print(f"Volatilidade ATM Média: {res['atm_iv']*100:.2f}%")
    print(f"Skew (Put OTM - Call OTM): {res['skew']*100:.2f}%")
    if res['skew'] > 0:
        print(">> Mercado está precificando MAIOR RISCO DE QUEDA (Puts mais caras que Calls).")
    else:
        print(">> Mercado está precificando MAIOR RISCO DE ALTA (Calls mais caras que Puts).")

if __name__ == "__main__":
    main()
