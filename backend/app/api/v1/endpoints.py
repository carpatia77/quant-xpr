from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.cross_analysis import run_cross_analysis
from app.db.database import get_db
from app.db.models import AnalysisResult

router = APIRouter()

@router.get("/summary/{ticker}")
def get_summary(ticker: str, db: Session = Depends(get_db)):
    result_dict = run_cross_analysis(ticker)
    
    # Save to DB
    db_result = AnalysisResult(
        ticker=result_dict["ticker"],
        markov_bull_prob=result_dict["markov_bull_prob"],
        markov_bear_prob=result_dict["markov_bear_prob"],
        iv_atm=result_dict["iv_atm"],
        skew=result_dict["skew"],
        signal=result_dict["signal"],
        status=result_dict["status"]
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    
    return result_dict
