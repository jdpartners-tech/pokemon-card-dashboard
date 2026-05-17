from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models import Card, PriceSnapshot, WatchlistItem
from backend.schemas import CardSummary, CardDetail, SnapshotPoint
from backend.scoring import calculate_trend_vs_days_ago

router = APIRouter(prefix="/cards", tags=["cards"])


def _snap_in_window(snap, cutoff) -> bool:
    from datetime import timezone
    dt = snap.scraped_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


def _latest_price(snaps, field: str):
    """Return the value of `field` from the most recent snapshot that has it."""
    for snap in sorted(snaps, key=lambda s: s.scraped_at, reverse=True):
        val = getattr(snap, field)
        if val:
            return float(val)
    return None


def _card_trends(snapshots):
    return {
        "trend_7d":  calculate_trend_vs_days_ago(snapshots, 7),
        "trend_30d": calculate_trend_vs_days_ago(snapshots, 30),
        "trend_90d": calculate_trend_vs_days_ago(snapshots, 90),
    }


def _build_summary(card: Card, trends: dict, watchlist_ids: set) -> CardSummary:
    snaps = card.snapshots
    return CardSummary(
        id=card.id,
        name=card.name,
        set_name=card.set_name,
        card_number=card.card_number,
        snkrdunk_price_hkd=_latest_price(snaps, "snkrdunk_price_hkd"),
        pricecharting_price_hkd=_latest_price(snaps, "pricecharting_price_hkd"),
        trend_7d=trends["trend_7d"],
        trend_30d=trends["trend_30d"],
        trend_90d=trends["trend_90d"],
        in_watchlist=card.id in watchlist_ids,
    )


@router.get("", response_model=list[CardSummary])
def get_cards(
    set: Optional[str] = Query(None),
    trending_up: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Card)
    if set:
        query = query.filter(Card.set_name.ilike(f"%{set}%"))
    if search:
        query = query.filter(Card.name.ilike(f"%{search}%"))
    cards = query.all()

    watchlist_ids = {w.card_id for w in db.query(WatchlistItem).all()}

    results = []
    for card in cards:
        trends = _card_trends(card.snapshots)
        if trending_up and not (trends["trend_7d"] and trends["trend_7d"] > 0):
            continue
        results.append((card, trends))

    # Sort by 7d trend descending (nulls last)
    results.sort(key=lambda x: x[1]["trend_7d"] or float("-inf"), reverse=True)

    return [_build_summary(card, trends, watchlist_ids) for card, trends in results]


@router.get("/{card_id}", response_model=CardDetail)
def get_card(card_id: str, db: Session = Depends(get_db)):
    import uuid as _uuid
    try:
        card_uuid = _uuid.UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Card not found")
    card = db.query(Card).filter(Card.id == card_uuid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    watchlist_ids = {w.card_id for w in db.query(WatchlistItem).all()}
    trends = _card_trends(card.snapshots)

    history = [
        SnapshotPoint(
            scraped_at=snap.scraped_at,
            snkrdunk_price_hkd=float(snap.snkrdunk_price_hkd) if snap.snkrdunk_price_hkd else None,
            pricecharting_price_hkd=float(snap.pricecharting_price_hkd) if snap.pricecharting_price_hkd else None,
        )
        for snap in sorted(card.snapshots, key=lambda x: x.scraped_at)
    ]

    return CardDetail(
        id=card.id,
        name=card.name,
        set_name=card.set_name,
        card_number=card.card_number,
        snkrdunk_price_hkd=_latest_price(card.snapshots, "snkrdunk_price_hkd"),
        pricecharting_price_hkd=_latest_price(card.snapshots, "pricecharting_price_hkd"),
        trend_7d=trends["trend_7d"],
        trend_30d=trends["trend_30d"],
        trend_90d=trends["trend_90d"],
        in_watchlist=card.id in watchlist_ids,
        history=history,
    )
