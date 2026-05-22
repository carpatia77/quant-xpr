import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.services.cross_analysis import run_cross_analysis
from app.db.database import get_db
from app.db.models import AnalysisResult
from app.core.rate_limit import limiter

router = APIRouter()

@router.get("/summary/{ticker}")
@limiter.limit("10/minute")
async def get_summary(request: Request, ticker: str, db: Session = Depends(get_db)):
    try:
        # Offload blocking computation to a separate thread to unblock the event loop
        # and enforce a maximum execution time of 15 seconds
        result_dict = await asyncio.wait_for(
            asyncio.to_thread(run_cross_analysis, ticker), 
            timeout=15.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Engine analysis timed out")

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

@router.get("/history/{ticker}")
@limiter.limit("20/minute")
async def get_history(request: Request, ticker: str, limit: int = 10, db: Session = Depends(get_db)):
    results = db.query(AnalysisResult).filter(AnalysisResult.ticker == ticker).order_by(AnalysisResult.timestamp.desc()).limit(limit).all()
    return results

@router.get("/assets")
@limiter.limit("20/minute")
async def get_assets(request: Request, db: Session = Depends(get_db)):
    assets = db.query(AnalysisResult.ticker).distinct().all()
    return [a[0] for a in assets]
