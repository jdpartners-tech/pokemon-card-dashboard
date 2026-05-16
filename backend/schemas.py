from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class CardSummary(BaseModel):
    id: UUID
    name: str
    set_name: str
    card_number: Optional[str]
    snkrdunk_price_hkd: Optional[float]
    pricecharting_price_hkd: Optional[float]
    trend_7d: float
    trend_30d: float
    arb_gap: float
    score: float
    in_watchlist: bool

    model_config = {"from_attributes": True}


class SnapshotPoint(BaseModel):
    scraped_at: datetime
    snkrdunk_price_hkd: Optional[float]
    pricecharting_price_hkd: Optional[float]

    model_config = {"from_attributes": True}


class CardDetail(BaseModel):
    id: UUID
    name: str
    set_name: str
    card_number: Optional[str]
    snkrdunk_price_hkd: Optional[float]
    pricecharting_price_hkd: Optional[float]
    score: float
    trend_7d: float
    trend_30d: float
    arb_gap: float
    in_watchlist: bool
    history: list[SnapshotPoint]

    model_config = {"from_attributes": True}


class WatchlistAdd(BaseModel):
    card_id: UUID
