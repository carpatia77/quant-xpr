import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.services.cross_analysis import run_cross_analysis
from app.db.database import get_db
from app.db.models import AnalysisResult
from app.core.rate_limit import limiter
from typing import Optional
from pydantic import BaseModel
from app.db.models import WatchlistItem
from app.services.data_fetcher import fetch_multiple_quotes

router = APIRouter()


@router.get("/summary/{ticker}")
@limiter.limit("10/minute")
async def get_summary(request: Request, ticker: str, rfr: Optional[float] = None, db: Session = Depends(get_db)):
    try:
        result_dict = await asyncio.wait_for(
            asyncio.to_thread(run_cross_analysis, ticker, rfr),
            timeout=55.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Engine analysis timed out")

    db_result = AnalysisResult(
        ticker=result_dict["ticker"],
        markov_bull_prob=result_dict["markov_bull_prob"],
        markov_bear_prob=result_dict["markov_bear_prob"],
        iv_atm=result_dict["iv_atm"],
        skew=result_dict["skew"],
        risk_free_rate=result_dict.get("risk_free_rate"),
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
    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.ticker == ticker)
        .order_by(AnalysisResult.timestamp.desc())
        .limit(limit)
        .all()
    )
    return results


@router.get("/assets")
@limiter.limit("20/minute")
async def get_assets(request: Request, db: Session = Depends(get_db)):
    assets = db.query(AnalysisResult.ticker).distinct().all()
    return [a[0] for a in assets]


class WatchlistCreate(BaseModel):
    ticker: str


@router.get("/watchlist/summary")
@limiter.limit("30/minute")
async def get_watchlist_summary(request: Request, db: Session = Depends(get_db)):
    """
    Retorna o ultimo AnalysisResult de cada ticker da watchlist,
    enriquecido com cotacao em tempo real via Brapi.
    """
    db_tickers = [
        item.ticker
        for item in db.query(WatchlistItem).order_by(WatchlistItem.added_at.asc()).all()
    ]
    default_tickers = [
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA",
        "B3SA3.SA", "ABEV3.SA", "WEGE3.SA", "ELET3.SA", "RENT3.SA"
    ]
    watchlist_tickers = list(db_tickers)
    for dt in default_tickers:
        if dt not in watchlist_tickers:
            watchlist_tickers.append(dt)

    # Busca cotacoes em batch via Brapi (substitui HG Brasil)
    real_time_data = await asyncio.to_thread(fetch_multiple_quotes, watchlist_tickers)

    results = []
    for ticker in watchlist_tickers:
        latest = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.ticker == ticker)
            .order_by(AnalysisResult.timestamp.desc())
            .first()
        )
        clean = ticker.replace(".SA", "")
        broad = real_time_data.get(clean, {})

        if latest:
            results.append({
                "ticker": latest.ticker,
                "signal": latest.signal,
                "iv_atm": latest.iv_atm,
                "skew": latest.skew,
                "risk_free_rate": latest.risk_free_rate,
                "markov_bull_prob": latest.markov_bull_prob,
                "markov_bear_prob": latest.markov_bear_prob,
                "price": broad.get("price", 0.0),
                "change_percent": broad.get("change_percent", 0.0),
                "company_name": broad.get("company_name", ticker),
            })
        else:
            results.append({
                "ticker": ticker,
                "signal": "WAITING_DATA",
                "iv_atm": 0.0,
                "skew": 0.0,
                "risk_free_rate": 0.0,
                "markov_bull_prob": 0.0,
                "markov_bear_prob": 0.0,
                "price": broad.get("price", 0.0),
                "change_percent": broad.get("change_percent", 0.0),
                "company_name": broad.get("company_name", ticker),
            })
    return results


@router.get("/watchlist")
@limiter.limit("30/minute")
async def get_watchlist(request: Request, db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).order_by(WatchlistItem.added_at.asc()).all()
    return [item.ticker for item in items]


@router.post("/watchlist")
@limiter.limit("10/minute")
async def add_watchlist_item(request: Request, item: WatchlistCreate, db: Session = Depends(get_db)):
    ticker = item.ticker.upper()
    existing = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker).first()
    if not existing:
        new_item = WatchlistItem(ticker=ticker)
        db.add(new_item)
        db.commit()
    return {"status": "success", "ticker": ticker}


@router.delete("/watchlist/{ticker}")
@limiter.limit("10/minute")
async def remove_watchlist_item(request: Request, ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper()
    item = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker).first()
    if item:
        db.delete(item)
        db.commit()
    return {"status": "success", "ticker": ticker}
