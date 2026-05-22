from app.engines.markov_hedge_fund_method.regime import label_regimes, build_transition_matrix, stationary_distribution
from app.engines.run_vol import get_vol_surface
from app.services.data_fetcher import fetch_ticker_data
from app.core.config import settings

def run_cross_analysis(ticker: str):
    # Get Volatility Data
    vol_data = get_vol_surface(ticker)
    
    # Extract metrics
    if "error" in vol_data:
        iv_atm = 0.0
        skew = 0.0
        smile_data = []
        vol_status = vol_data["error"]
    else:
        iv_atm = float(vol_data.get("atm_iv", 0.0))
        skew = float(vol_data.get("skew", 0.0))
        smile_data = vol_data.get("smile_data", [])
        vol_status = "ok"

    # Get Markov Data
    try:
        df = fetch_ticker_data(ticker, years=10)
        close = df["Close"].dropna()
        labels = label_regimes(close, window=20, threshold=0.02)
        P = build_transition_matrix(labels)
        pi = stationary_distribution(P)
        current_state = int(labels.iloc[-1])
        markov_bull_prob = float(P[current_state, 2])
        markov_bear_prob = float(P[current_state, 0])
        
        # Build regime history (last 30 days) for charting
        recent_close = close.tail(30)
        recent_labels = labels.tail(30)
        regime_history = [
            {"date": str(d.date()), "price": float(p), "regime": int(r)}
            for d, p, r in zip(recent_close.index, recent_close.values, recent_labels.values)
        ]
        
        markov_status = "ok"
    except Exception as e:
        markov_bull_prob = 0.0
        markov_bear_prob = 0.0
        regime_history = []
        markov_status = str(e)
    
    # Generate Signal
    if markov_status == "ok":
        if markov_bull_prob > settings.BULL_THRESHOLD and iv_atm < settings.IV_MAX_CHEAP and vol_status == "ok":
            signal = "long_vol"
        elif markov_bull_prob > settings.BULL_THRESHOLD and skew > settings.SKEW_MIN_REVERSAL and vol_status == "ok":
            signal = "risk_reversal"
        elif markov_bull_prob > settings.BULL_THRESHOLD:
            signal = "directional_bull"
        elif markov_bear_prob > settings.BULL_THRESHOLD:
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
        "status": f"Markov: {markov_status} | Vol: {vol_status}",
        "smile_data": smile_data,
        "regime_history": regime_history
    }
