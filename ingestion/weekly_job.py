import os
import sys

# Add backend directory to sys.path so we can import the quant engine and database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.db.database import SessionLocal
from app.db.models import AnalysisResult
from app.services.cross_analysis import run_cross_analysis

TICKERS_TO_MONITOR = [
    "SPY",      # S&P 500 ETF
    "QQQ",      # Nasdaq 100 ETF
    "PETR4.SA", # Petrobras (B3)
    "VALE3.SA", # Vale (B3)
    "BOVA11.SA" # Ibovespa ETF
]

def main():
    print(f"🚀 Starting Weekly Ingestion Job for {len(TICKERS_TO_MONITOR)} assets...")
    
    # Initialize DB Session
    db = SessionLocal()
    
    try:
        for ticker in TICKERS_TO_MONITOR:
            print(f"📊 Analyzing {ticker}...")
            try:
                result = run_cross_analysis(ticker)
                
                # Save to database
                db_result = AnalysisResult(
                    ticker=result["ticker"],
                    markov_bull_prob=result["markov_bull_prob"],
                    markov_bear_prob=result["markov_bear_prob"],
                    iv_atm=result["iv_atm"],
                    skew=result["skew"],
                    signal=result["signal"],
                    status=result["status"]
                )
                db.add(db_result)
                db.commit()
                print(f"✅ Saved result for {ticker} -> Signal: {result['signal']}")
                
            except Exception as e:
                db.rollback()
                print(f"❌ Error analyzing {ticker}: {e}")
                
    finally:
        db.close()
        print("🏁 Weekly Ingestion Job completed.")

if __name__ == "__main__":
    main()
