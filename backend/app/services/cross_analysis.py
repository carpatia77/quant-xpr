from app.engines.markov_hedge_fund_method.regime import label_regimes, build_transition_matrix, stationary_distribution
from app.engines.run_vol import get_vol_surface
from app.services.data_fetcher import fetch_ticker_data
from app.services.risk_free_rate import get_selic_anual
from app.services.hg_brasil import fetch_stock_quote
from app.core.config import settings

def run_cross_analysis(ticker: str):
    # Fetch risk free rate first
    risk_free_rate = 0.0
    risk_free_rate_source = "Zero (International Asset)"
    if ticker.endswith(".SA"):
        risk_free_rate = get_selic_anual()
        risk_free_rate_source = "BCB SGS 11 (Selic Over)"

    # Fetch ticker data once for both Vol and Markov
    try:
        df = fetch_ticker_data(ticker, years=10)
    except Exception as e:
        df = None

    # Get Volatility Data using Forward Adjustment
    vol_data = get_vol_surface(ticker, risk_free_rate, df=df)
    
    # Extract metrics
    if "error" in vol_data:
        iv_atm = 0.0
        skew = 0.0
        smile_data = []
        vol_term_structure = []
        vol_status = vol_data["error"]
    else:
        iv_atm = float(vol_data.get("atm_iv", 0.0))
        skew = float(vol_data.get("skew", 0.0))
        smile_data = vol_data.get("smile_data", [])
        vol_term_structure = vol_data.get("vol_term_structure", [])
        vol_status = "ok"

    # Get Markov Data
    try:
        if df is None:
            raise ValueError("No historical data available")
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
        dynamic_skew_threshold = settings.SKEW_MIN_REVERSAL + (0.5 * risk_free_rate)
        
        if markov_bull_prob > settings.BULL_THRESHOLD and iv_atm < settings.IV_MAX_CHEAP and vol_status == "ok":
            signal = "long_vol"
        elif markov_bull_prob > settings.BULL_THRESHOLD and skew > dynamic_skew_threshold and vol_status == "ok":
            signal = "risk_reversal"
        elif markov_bull_prob > settings.BULL_THRESHOLD:
            signal = "directional_bull"
        elif markov_bear_prob > settings.BULL_THRESHOLD:
            signal = "directional_bear"
        else:
            signal = "neutral"
    else:
        signal = "error_fetching_data"
        
    # Fetch broad data from HG Brasil
    broad_data = fetch_stock_quote(ticker)
        
    return {
        "ticker": ticker,
        "company_name": broad_data.get("company_name", ticker),
        "spot_price": broad_data.get("price", df["Close"].iloc[-1] if df is not None and not df.empty else 0.0),
        "change_percent": broad_data.get("change_percent", 0.0),
        "market_cap": broad_data.get("market_cap", 0.0),
        "markov_bull_prob": round(markov_bull_prob, 4),
        "markov_bear_prob": round(markov_bear_prob, 4),
        "iv_atm": round(iv_atm, 4),
        "skew": round(skew, 4),
        "signal": signal,
        "status": f"Markov: {markov_status} | Vol: {vol_status}",
        "smile_data": smile_data,
        "vol_term_structure": vol_term_structure,
        "regime_history": regime_history,
        "risk_free_rate": round(risk_free_rate, 6),
        "risk_free_rate_source": risk_free_rate_source
    }
