from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from app.db.database import Base
from datetime import datetime, timezone

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    markov_bull_prob = Column(Float)
    markov_bear_prob = Column(Float)
    iv_atm = Column(Float)
    skew = Column(Float)
    risk_free_rate = Column(Float, nullable=True)
    signal = Column(String)
    status = Column(String)

Index("ix_analysis_ticker_ts", AnalysisResult.ticker, AnalysisResult.timestamp)

class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    ticker = Column(String, primary_key=True, index=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
