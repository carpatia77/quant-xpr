import time
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.data_fetcher import fetch_ticker_data
from backend.app.services.risk_free_rate import get_selic_anual
from backend.app.engines.run_vol import get_vol_surface

def test_timing():
    print("Testing get_selic_anual...")
    t0 = time.time()
    try:
        rfr = get_selic_anual()
        print(f"Selic: {rfr} (took {time.time()-t0:.2f}s)")
    except Exception as e:
        print(f"Failed: {e}")

    print("Testing fetch_ticker_data...")
    t0 = time.time()
    try:
        df = fetch_ticker_data("PETR4.SA", years=10)
        print(f"DF shape: {df.shape} (took {time.time()-t0:.2f}s)")
    except Exception as e:
        print(f"Failed: {e}")
        df = None

    print("Testing get_vol_surface...")
    t0 = time.time()
    try:
        vol = get_vol_surface("PETR4.SA", 0.1, df=df)
        print(f"Vol status: {vol.get('error', 'ok')} (took {time.time()-t0:.2f}s)")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == '__main__':
    test_timing()
