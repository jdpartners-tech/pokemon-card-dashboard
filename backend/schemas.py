# backend/schemas.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date
from typing import Optional


class CardSummary(BaseModel):
    id: UUID
    name: str
    set_name: str
    card_number: Optional[str]
    image_url: Optional[str]
    accent_color: Optional[str]
    snkrdunk_price_hkd: Optional[float]
    pricecharting_price_hkd: Optional[float]
    psa_population: Optional[int]
    trend_7d: Optional[float]
    trend_30d: Optional[float]
    trend_90d: Optional[float]
    trend_1y: Optional[float]
    pct_from_ath: Optional[float]
    trend_consistency: int
    in_watchlist: bool

    model_config = {"from_attributes": True}


class SnapshotPoint(BaseModel):
    scraped_at: datetime
    snkrdunk_price_hkd: Optional[float]
    pricecharting_price_hkd: Optional[float]

    model_config = {"from_attributes": True}


class CardDetail(CardSummary):
    snkrdunk_url: Optional[str]
    pricecharting_url: Optional[str]
    sales_per_day: Optional[float]
    ath: Optional[float]
    ath_date: Optional[datetime]
    history: list[SnapshotPoint]


class WatchlistAdd(BaseModel):
    card_id: UUID


class PortfolioItemOut(BaseModel):
    id: UUID
    card_id: UUID
    name: str
    set_name: str
    card_number: Optional[str]
    image_url: Optional[str]
    accent_color: Optional[str]
    psa_population: Optional[int]
    purchase_price_hkd: float
    purchased_at: date
    current_price_hkd: Optional[float]
    pnl_hkd: Optional[float]
    pnl_pct: Optional[float]
    trend_30d: Optional[float]

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    items: list[PortfolioItemOut]
    total_invested: float
    total_current_value: float
    total_pnl_hkd: float
    total_pnl_pct: Optional[float]


class PortfolioAdd(BaseModel):
    card_id: UUID
    purchase_price_hkd: float
    purchased_at: date
