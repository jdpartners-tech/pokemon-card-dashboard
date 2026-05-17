# backend/routers/portfolio.py
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Card, PortfolioItem
from backend.schemas import PortfolioAdd, PortfolioItemOut, PortfolioSummary
from backend.routers.cards import _latest_price, _card_metrics

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioSummary)
def get_portfolio(db: Session = Depends(get_db)):
    items = db.query(PortfolioItem).all()
    out = []
    total_invested = 0.0
    total_current = 0.0

    for item in items:
        card = item.card
        current = _latest_price(card.snapshots, "pricecharting_price_hkd") or \
                  _latest_price(card.snapshots, "snkrdunk_price_hkd")
        paid = float(item.purchase_price_hkd)
        pnl_hkd = (current - paid) if current else None
        pnl_pct = ((current - paid) / paid * 100) if current and paid else None
        metrics = _card_metrics(card.snapshots)
        total_invested += paid
        if current:
            total_current += current
        out.append(PortfolioItemOut(
            id=item.id,
            card_id=item.card_id,
            name=card.name,
            set_name=card.set_name,
            card_number=card.card_number,
            image_url=card.image_url,
            accent_color=card.accent_color,
            psa_population=card.psa_population,
            purchase_price_hkd=paid,
            purchased_at=item.purchased_at,
            current_price_hkd=current,
            pnl_hkd=round(pnl_hkd, 2) if pnl_hkd is not None else None,
            pnl_pct=round(pnl_pct, 2) if pnl_pct is not None else None,
            trend_30d=metrics["trend_30d"],
        ))

    pnl_total = total_current - total_invested
    pnl_pct_total = (pnl_total / total_invested * 100) if total_invested else None
    return PortfolioSummary(
        items=sorted(out, key=lambda x: x.pnl_pct or float("-inf"), reverse=True),
        total_invested=round(total_invested, 2),
        total_current_value=round(total_current, 2),
        total_pnl_hkd=round(pnl_total, 2),
        total_pnl_pct=round(pnl_pct_total, 2) if pnl_pct_total is not None else None,
    )


@router.post("", response_model=dict)
def add_portfolio_item(body: PortfolioAdd, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == body.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    item = PortfolioItem(
        id=uuid.uuid4(),
        card_id=body.card_id,
        purchase_price_hkd=Decimal(str(body.purchase_price_hkd)),
        purchased_at=body.purchased_at,
    )
    db.add(item)
    db.commit()
    return {"ok": True, "id": str(item.id)}


@router.delete("/{item_id}", response_model=dict)
def delete_portfolio_item(item_id: str, db: Session = Depends(get_db)):
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")
    item = db.query(PortfolioItem).filter(PortfolioItem.id == item_uuid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
