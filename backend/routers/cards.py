# backend/routers/cards.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models import Card, PriceSnapshot, WatchlistItem
from backend.schemas import CardSummary, CardDetail, SnapshotPoint
from backend.scoring import (
    calculate_trend_vs_days_ago, calculate_trend_all_time,
    calculate_ath, calculate_pct_from_ath, calculate_trend_consistency,
)

router = APIRouter(prefix="/cards", tags=["cards"])


def _latest_price(snaps, field: str):
    for snap in sorted(snaps, key=lambda s: s.scraped_at, reverse=True):
        val = getattr(snap, field)
        if val:
            return float(val)
    return None


def _card_metrics(snapshots: list) -> dict:
    ath, ath_date = calculate_ath(snapshots)
    return {
        "trend_1m":          calculate_trend_vs_days_ago(snapshots, 30),
        "trend_3m":          calculate_trend_vs_days_ago(snapshots, 90),
        "trend_6m":          calculate_trend_vs_days_ago(snapshots, 180),
        "trend_1y":          calculate_trend_vs_days_ago(snapshots, 365),
        "trend_all":         calculate_trend_all_time(snapshots),
        "pct_from_ath":      calculate_pct_from_ath(snapshots),
        "trend_consistency": calculate_trend_consistency(snapshots),
        "ath":               ath,
        "ath_date":          ath_date,
    }


def _build_summary(card: Card, metrics: dict, watchlist_ids: set) -> CardSummary:
    snaps = card.snapshots
    return CardSummary(
        id=card.id,
        name=card.name,
        set_name=card.set_name,
        card_number=card.card_number,
        image_url=card.image_url,
        accent_color=card.accent_color,
        snkrdunk_price_hkd=_latest_price(snaps, "snkrdunk_price_hkd"),
        pricecharting_price_hkd=_latest_price(snaps, "pricecharting_price_hkd"),
        psa_population=card.psa_population,
        trend_1m=metrics["trend_1m"],
        trend_3m=metrics["trend_3m"],
        trend_6m=metrics["trend_6m"],
        trend_1y=metrics["trend_1y"],
        trend_all=metrics["trend_all"],
        pct_from_ath=metrics["pct_from_ath"],
        trend_consistency=metrics["trend_consistency"],
        in_watchlist=card.id in watchlist_ids,
    )


@router.get("", response_model=list[CardSummary])
def get_cards(
    sort: str = Query("trend_1m"),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    positive_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    trend_sorts = {"trend_1m", "trend_3m", "trend_6m", "trend_1y", "trend_all"}
    valid_sorts = trend_sorts | {"price_hkd", "name"}
    if sort not in valid_sorts:
        sort = "trend_1m"

    query = db.query(Card)
    if search:
        query = query.filter(Card.name.ilike(f"%{search}%"))
    cards = query.all()

    watchlist_ids = {w.card_id for w in db.query(WatchlistItem).all()}

    results = []
    for card in cards:
        metrics = _card_metrics(card.snapshots)

        if sort in trend_sorts:
            trend = metrics[sort]
            if positive_only and (trend is None or trend <= 0):
                continue
        else:
            if positive_only:
                # positive_only only makes sense with trend sorts — ignore for price/name
                pass

        results.append((card, metrics))

    if sort in trend_sorts:
        results.sort(
            key=lambda x: x[1][sort] if x[1][sort] is not None else float("-inf"),
            reverse=True,
        )
    elif sort == "price_hkd":
        results.sort(
            key=lambda x: float(
                _latest_price(x[0].snapshots, "pricecharting_price_hkd") or
                _latest_price(x[0].snapshots, "snkrdunk_price_hkd") or 0
            ),
            reverse=True,
        )
    elif sort == "name":
        results.sort(key=lambda x: x[0].name.lower())

    results = results[:limit]
    return [_build_summary(card, metrics, watchlist_ids) for card, metrics in results]


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
    metrics = _card_metrics(card.snapshots)

    history = [
        SnapshotPoint(
            scraped_at=snap.scraped_at,
            snkrdunk_price_hkd=float(snap.snkrdunk_price_hkd) if snap.snkrdunk_price_hkd else None,
            pricecharting_price_hkd=float(snap.pricecharting_price_hkd) if snap.pricecharting_price_hkd else None,
        )
        for snap in sorted(card.snapshots, key=lambda x: x.scraped_at)
    ]

    return CardDetail(
        **_build_summary(card, metrics, watchlist_ids).model_dump(),
        snkrdunk_url=card.snkrdunk_url,
        pricecharting_url=card.pricecharting_url,
        sales_per_day=float(card.sales_per_day) if card.sales_per_day else None,
        ath=metrics["ath"],
        ath_date=metrics["ath_date"],
        history=history,
    )
