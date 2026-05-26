import pandas as pd
import numpy as np
import math
from datetime import datetime
from scipy.interpolate import interp1d
import structlog
import yfinance as yf

logger = structlog.get_logger(__name__)

def yang_zhang(price_data: pd.DataFrame, window: int = 30, trading_periods: int = 252) -> float:
    """Calcula a volatilidade histórica usando o estimador de Yang-Zhang."""
    if len(price_data) < window:
        return 0.0
        
    log_ho = (price_data['High'] / price_data['Open']).apply(np.log)
    log_lo = (price_data['Low'] / price_data['Open']).apply(np.log)
    log_co = (price_data['Close'] / price_data['Open']).apply(np.log)
    
    log_oc = (price_data['Open'] / price_data['Close'].shift(1)).apply(np.log)
    log_oc_sq = log_oc**2
    
    log_cc = (price_data['Close'] / price_data['Close'].shift(1)).apply(np.log)
    log_cc_sq = log_cc**2
    
    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    
    close_vol = log_cc_sq.rolling(window=window).sum() * (1.0 / (window - 1.0))
    open_vol = log_oc_sq.rolling(window=window).sum() * (1.0 / (window - 1.0))
    window_rs = rs.rolling(window=window).sum() * (1.0 / (window - 1.0))

    k = 0.34 / (1.34 + ((window + 1) / (window - 1)))
    result = (open_vol + k * close_vol + (1 - k) * window_rs).apply(np.sqrt) * np.sqrt(trading_periods)
    
    return float(result.dropna().iloc[-1])

def build_term_structure(days: list[int], ivs: list[float]):
    """Constrói uma interpolação linear (Spline) para a Term Structure de volatilidade."""
    days_arr = np.array(days)
    ivs_arr = np.array(ivs)

    sort_idx = days_arr.argsort()
    days_arr = days_arr[sort_idx]
    ivs_arr = ivs_arr[sort_idx]

    spline = interp1d(days_arr, ivs_arr, kind='linear', fill_value="extrapolate")

    def term_spline(dte: float) -> float:
        if dte < days_arr[0]:  
            return float(ivs_arr[0])
        elif dte > days_arr[-1]:
            return float(ivs_arr[-1])
        else:  
            return float(spline(dte))

    return term_spline

def analyze_premium(ticker: str, df: pd.DataFrame) -> dict:
    """
    Orquestra o motor de Volatility Premium:
    - Realized Vol (RV30) vs Implied Vol (IV30)
    - Term Structure Slope (Backwardation/Contango)
    - Expected Move via ATM Straddle
    """
    if df is None or df.empty:
        return {"error": "Sem dados históricos (OHLCV) para RV."}

    # Calcula RV30 via Yang-Zhang
    rv30 = yang_zhang(df, window=30)

    # Verifica volume médio de 30 dias
    try:
        avg_volume = df['Volume'].rolling(30).mean().dropna().iloc[-1]
    except Exception:
        avg_volume = 0

    # Busca a cadeia de opções inteira no yfinance (múltiplos vencimentos)
    try:
        stock = yf.Ticker(ticker)
        exp_dates = list(stock.options)
        if not exp_dates:
            return {"error": "Sem opções disponíveis no yfinance."}
    except Exception as e:
        logger.error("vol_premium_yfinance_error", ticker=ticker, error=str(e))
        return {"error": f"Erro yfinance: {str(e)}"}

    underlying_price = float(df['Close'].iloc[-1])
    
    atm_iv = {}
    straddle = None 
    
    today = datetime.today().date()
    
    for i, exp_date in enumerate(exp_dates[:5]):  # Limita aos primeiros 5 vencimentos líquidos
        try:
            chain = stock.option_chain(exp_date)
            calls = chain.calls
            puts = chain.puts

            if calls.empty or puts.empty:
                continue

            # Encontra Strike ATM
            call_idx = (calls['strike'] - underlying_price).abs().idxmin()
            call_iv = calls.loc[call_idx, 'impliedVolatility']

            put_idx = (puts['strike'] - underlying_price).abs().idxmin()
            put_iv = puts.loc[put_idx, 'impliedVolatility']

            atm_iv_value = (call_iv + put_iv) / 2.0
            atm_iv[exp_date] = atm_iv_value

            # Calcula Expected Move do primeiro vencimento líquido
            if i == 0 and straddle is None:
                call_bid = calls.loc[call_idx, 'bid']
                call_ask = calls.loc[call_idx, 'ask']
                put_bid = puts.loc[put_idx, 'bid']
                put_ask = puts.loc[put_idx, 'ask']
                
                call_mid = (call_bid + call_ask) / 2.0 if (call_bid and call_ask) else call_iv * underlying_price * 0.1 # proxy rough se sem bid/ask
                put_mid = (put_bid + put_ask) / 2.0 if (put_bid and put_ask) else put_iv * underlying_price * 0.1

                if call_mid and put_mid:
                    straddle = (call_mid + put_mid)
        except Exception:
            continue

    if not atm_iv:
        return {"error": "Não foi possível calcular ATM IV nas opções."}

    # Constrói Spline e Term Structure
    dtes = []
    ivs = []
    for exp_date, iv in atm_iv.items():
        exp_date_obj = datetime.strptime(exp_date, "%Y-%m-%d").date()
        days_to_expiry = max((exp_date_obj - today).days, 1)
        dtes.append(days_to_expiry)
        ivs.append(iv)

    if len(dtes) < 2:
        return {"error": "Menos de 2 vencimentos líquidos. Impossível gerar Term Structure."}

    term_spline = build_term_structure(dtes, ivs)
    
    # Métricas Quant
    ts_slope_0_45 = (term_spline(45) - term_spline(dtes[0])) / max(45 - dtes[0], 1)
    iv30 = term_spline(30)
    iv30_rv30 = iv30 / rv30 if rv30 > 0 else 0
    expected_move = round(straddle / underlying_price * 100, 2) if straddle and underlying_price > 0 else 0.0

    # Condições Booleanas
    avg_volume_pass = avg_volume >= 1500000
    iv30_rv30_pass = iv30_rv30 >= 1.25
    ts_slope_pass = ts_slope_0_45 <= -0.00406

    # Bias Recommendation
    if avg_volume_pass and iv30_rv30_pass and ts_slope_pass:
        bias_recommendation = "Recommended"
    elif ts_slope_pass and ((avg_volume_pass and not iv30_rv30_pass) or (iv30_rv30_pass and not avg_volume_pass)):
        bias_recommendation = "Consider"
    else:
        bias_recommendation = "Avoid"

    return {
        "avg_volume": int(avg_volume),
        "avg_volume_pass": bool(avg_volume_pass),
        "iv30_rv30": round(iv30_rv30, 2),
        "iv30_rv30_pass": bool(iv30_rv30_pass),
        "ts_slope_0_45": round(ts_slope_0_45, 5),
        "ts_slope_pass": bool(ts_slope_pass),
        "expected_move_pct": float(expected_move),
        "bias_recommendation": bias_recommendation,
        "error": None
    }
