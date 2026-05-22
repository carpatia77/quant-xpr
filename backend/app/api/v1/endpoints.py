from fastapi import APIRouter
from app.services.cross_analysis import run_cross_analysis

router = APIRouter()

@router.get("/summary/{ticker}")
def get_summary(ticker: str):
    # Stub return to be replaced with actual calculated data
    return run_cross_analysis(ticker)
