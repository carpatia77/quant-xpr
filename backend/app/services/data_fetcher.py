import time
import pandas as pd
import yfinance as yf

def fetch_ticker_data(ticker: str, years: int = 10) -> pd.DataFrame:
    """Fetch via yfinance with one retry; raise on persistent empty."""
    end = pd.Timestamp.now(tz="UTC").normalize()
    start = end - pd.DateOffset(years=years)

    for attempt in (1, 2):
        try:
            df = yf.download(
                ticker,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
                timeout=8,
            )
        except Exception as exc:
            print(f"  ! yfinance error on attempt {attempt}: {exc}")
            df = pd.DataFrame()

        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df

        if attempt == 1:
            print(f"  ! yfinance returned empty data — retrying in 2s.")
            time.sleep(2)

    raise RuntimeError(
        f"yfinance returned empty data for {ticker} after retry. "
        "Yahoo may be rate-limiting. Try again in a few minutes."
    )
