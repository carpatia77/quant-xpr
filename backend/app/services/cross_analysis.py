import structlog
from app.engines.markov_hedge_fund_method.regime import label_regimes, build_transition_matrix, stationary_distribution
from app.engines.run_vol import get_vol_surface
from app.engines.vol_premium import analyze_premium
from app.services.data_fetcher import fetch_ticker_data, fetch_quote
from app.services.risk_free_rate import get_selic_anual
from app.core.config import settings

logger = structlog.get_logger(__name__)

def run_cross_analysis(ticker: str, custom_rfr: float = None, brapi_token: str = None, hg_token: str = None):
    # --- Risk-free rate ---
    risk_free_rate = 0.0
    risk_free_rate_source = "Zero (International Asset)"
    if custom_rfr is not None:
        risk_free_rate = custom_rfr
        risk_free_rate_source = "Custom Override"
    elif ticker.endswith(".SA"):
        risk_free_rate = get_selic_anual()
        risk_free_rate_source = "Taxa Selic"

    # --- Historical OHLCV via Brapi ---
    df = None
    try:
        df = fetch_ticker_data(ticker, years=1, brapi_token=brapi_token)
    except Exception as e:
        logger.error("data_fetcher_failed", ticker=ticker, error=str(e))

    # --- Volatility surface via yfinance options ---
    vol_data = get_vol_surface(ticker, risk_free_rate, df=df)
    if "error" in vol_data:
        iv_atm = 0.0
        skew = 0.0
        smile_data = []
        vol_term_structure = []
        vol_status = vol_data["error"]
        logger.warning("vol_surface_error", ticker=ticker, error=vol_status)
    else:
        iv_atm = float(vol_data.get("atm_iv", 0.0))
        skew = float(vol_data.get("skew", 0.0))
        smile_data = vol_data.get("smile_data", [])
        vol_term_structure = vol_data.get("vol_term_structure", [])
        vol_status = "ok"

    # --- Markov regime engine ---
    markov_bull_prob = 0.0
    markov_bear_prob = 0.0
    regime_history = []
    markov_status = "no_data"

    if df is not None and not df.empty:
        try:
            close = df["Close"].dropna()
            labels = label_regimes(close, window=20, threshold=0.02)
            P = build_transition_matrix(labels)
            stationary_distribution(P)
            current_state = int(labels.iloc[-1])
            markov_bull_prob = float(P[current_state, 2])
            markov_bear_prob = float(P[current_state, 0])
            recent_close = close.tail(30)
            recent_labels = labels.tail(30)
            regime_history = [
                {"date": str(d.date()), "price": float(p), "regime": int(r)}
                for d, p, r in zip(recent_close.index, recent_close.values, recent_labels.values)
            ]
            markov_status = "ok"
        except Exception as e:
            markov_status = str(e)
            logger.error("markov_engine_failed", ticker=ticker, error=str(e))
    else:
        logger.error("markov_skipped_no_df", ticker=ticker)

    # --- Signal generation ---
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
        signal = f"error_{markov_status[:30]}"

    # --- Spot price + metadata via Brapi quote ---
    quote = fetch_quote(ticker, brapi_token=brapi_token)
    spot_price = quote.get("price") or (float(df["Close"].iloc[-1]) if df is not None and not df.empty else 0.0)

    # --- Volatility Premium Engine (Term Structure & RV vs IV) ---
    vol_premium = analyze_premium(ticker, df)

    return {
        "ticker": ticker,
        "company_name": quote.get("company_name", ticker),
        "spot_price": spot_price,
        "change_percent": quote.get("change_percent", 0.0),
        "market_cap": quote.get("market_cap", 0.0),
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
        "risk_free_rate_source": risk_free_rate_source,
        "vol_premium": vol_premium,
    }
