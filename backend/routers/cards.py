from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional
from backend.database import get_db
from backend.models import Card, PriceSnapshot, WatchlistItem
from backend.schemas import CardSummary, CardDetail, SnapshotPoint
from backend.scoring import score_cards

router = APIRouter(prefix="/cards", tags=["cards"])


def _snap_in_window(snap, cutoff_utc: datetime) -> bool:
    """Compare snapshot datetime to cutoff, handling naive datetimes from SQLite."""
    ts = snap.scraped_at
    if ts is None:
        return False
    if ts.tzinfo is None:
        # SQLite returns naive datetimes; compare against naive cutoff
        return ts >= cutoff_utc.replace(tzinfo=None)
    return ts >= cutoff_utc


def _build_summary(scored: dict, watchlist_ids: set) -> CardSummary:
    card = scored["card"]
    snaps = sorted(card.snapshots, key=lambda s: s.scraped_at, reverse=True)
    latest = snaps[0] if snaps else None
    return CardSummary(
        id=card.id,
        name=card.name,
        set_name=card.set_name,
        card_number=card.card_number,
        snkrdunk_price_hkd=float(latest.snkrdunk_price_hkd) if latest and latest.snkrdunk_price_hkd else None,
        pricecharting_price_hkd=float(latest.pricecharting_price_hkd) if latest and latest.pricecharting_price_hkd else None,
        trend_7d=scored["trend_7d"],
        trend_30d=scored["trend_30d"],
        arb_gap=scored["arb_gap"],
        score=scored["score"],
        in_watchlist=card.id in watchlist_ids,
    )


@router.get("", response_model=list[CardSummary])
def get_cards(
    set: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
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
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    card_snaps = [(c, [s for s in c.snapshots if _snap_in_window(s, cutoff)]) for c in cards]
    scored = score_cards(card_snaps)

    if min_score is not None:
        scored = [s for s in scored if s["score"] >= min_score]

    return [_build_summary(s, watchlist_ids) for s in scored]


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
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    snaps_30d = [s for s in card.snapshots if _snap_in_window(s, cutoff)]
    scored = score_cards([(card, snaps_30d)])
    s = scored[0]

    history = [
        SnapshotPoint(
            scraped_at=snap.scraped_at,
            snkrdunk_price_hkd=float(snap.snkrdunk_price_hkd) if snap.snkrdunk_price_hkd else None,
            pricecharting_price_hkd=float(snap.pricecharting_price_hkd) if snap.pricecharting_price_hkd else None,
        )
        for snap in sorted(card.snapshots, key=lambda x: x.scraped_at)
        if _snap_in_window(snap, cutoff)
    ]

    latest = sorted(card.snapshots, key=lambda s: s.scraped_at, reverse=True)
    latest_snap = latest[0] if latest else None

    return CardDetail(
        id=card.id,
        name=card.name,
        set_name=card.set_name,
        card_number=card.card_number,
        snkrdunk_price_hkd=float(latest_snap.snkrdunk_price_hkd) if latest_snap and latest_snap.snkrdunk_price_hkd else None,
        pricecharting_price_hkd=float(latest_snap.pricecharting_price_hkd) if latest_snap and latest_snap.pricecharting_price_hkd else None,
        score=s["score"],
        trend_7d=s["trend_7d"],
        trend_30d=s["trend_30d"],
        arb_gap=s["arb_gap"],
        in_watchlist=card.id in watchlist_ids,
        history=history,
    )
