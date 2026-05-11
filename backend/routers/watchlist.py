from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from backend.database import get_db
from backend.models import Card, WatchlistItem
from backend.schemas import CardSummary, WatchlistAdd
from backend.scoring import score_cards
from backend.routers.cards import _build_summary, _snap_in_window

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[CardSummary])
def get_watchlist(db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).all()
    watchlist_ids = {w.card_id for w in items}
    cards = [item.card for item in items]
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    card_snaps = [(c, [s for s in c.snapshots if _snap_in_window(s, cutoff)]) for c in cards]
    scored = score_cards(card_snaps)
    return [_build_summary(s, watchlist_ids) for s in scored]


@router.post("", response_model=dict)
def add_to_watchlist(body: WatchlistAdd, db: Session = Depends(get_db)):
    existing = db.query(WatchlistItem).filter(WatchlistItem.card_id == body.card_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already in watchlist")
    card = db.query(Card).filter(Card.id == body.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.add(WatchlistItem(card_id=body.card_id))
    db.commit()
    return {"ok": True}


@router.delete("/{card_id}", response_model=dict)
def remove_from_watchlist(card_id: str, db: Session = Depends(get_db)):
    import uuid as _uuid
    try:
        card_uuid = _uuid.UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    item = db.query(WatchlistItem).filter(WatchlistItem.card_id == card_uuid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    db.delete(item)
    db.commit()
    return {"ok": True}
