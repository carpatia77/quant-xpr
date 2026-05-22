from app.engines.markov_hedge_fund_method.run import _fetch_with_retry
from app.engines.markov_hedge_fund_method.regime import label_regimes, build_transition_matrix, stationary_distribution
from app.engines.run_vol import get_vol_surface

def run_cross_analysis(ticker: str):
    # Get Volatility Data
    vol_data = get_vol_surface(ticker)
    
    # Extract metrics
    if "error" in vol_data:
        iv_atm = 0.0
        skew = 0.0
        vol_status = vol_data["error"]
    else:
        iv_atm = float(vol_data.get("atm_iv", 0.0))
        skew = float(vol_data.get("skew", 0.0))
        vol_status = "ok"

    # Get Markov Data
    try:
        df = _fetch_with_retry(ticker, years=10)
        import pandas as pd
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"].dropna()
        labels = label_regimes(close, window=20, threshold=0.02)
        P = build_transition_matrix(labels)
        pi = stationary_distribution(P)
        current_state = int(labels.iloc[-1])
        markov_bull_prob = float(P[current_state, 2])
        markov_bear_prob = float(P[current_state, 0])
        markov_status = "ok"
    except Exception as e:
        markov_bull_prob = 0.0
        markov_bear_prob = 0.0
        markov_status = str(e)
    
    # Generate Signal
    if markov_status == "ok":
        if markov_bull_prob > 0.5 and iv_atm < 0.35 and vol_status == "ok":
            signal = "long_vol"
        elif markov_bull_prob > 0.5 and skew > 0.02 and vol_status == "ok":
            signal = "risk_reversal"
        elif markov_bull_prob > 0.5:
            signal = "directional_bull"
        elif markov_bear_prob > 0.5:
            signal = "directional_bear"
        else:
            signal = "neutral"
    else:
        signal = "error_fetching_data"
        
    return {
        "ticker": ticker,
        "markov_bull_prob": round(markov_bull_prob, 4),
        "markov_bear_prob": round(markov_bear_prob, 4),
        "iv_atm": round(iv_atm, 4),
        "skew": round(skew, 4),
        "signal": signal,
        "status": f"Markov: {markov_status} | Vol: {vol_status}"
    }
