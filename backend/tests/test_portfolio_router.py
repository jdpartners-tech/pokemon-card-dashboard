# backend/tests/test_portfolio_router.py
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from backend.models import Card, PriceSnapshot, PortfolioItem


def _seed_card_with_price(db, name="Pikachu"):
    card = Card(id=uuid.uuid4(), name=name, set_name="Base Set", card_number="58")
    snap = PriceSnapshot(
        id=uuid.uuid4(), card_id=card.id,
        pricecharting_price_hkd=Decimal("10000"),
        scraped_at=datetime.now(timezone.utc),
    )
    db.add(card); db.add(snap); db.commit()
    return card


def test_add_and_get_portfolio_item(client, db):
    card = _seed_card_with_price(db)
    resp = client.post("/portfolio", json={
        "card_id": str(card.id),
        "purchase_price_hkd": 8000.0,
        "purchased_at": "2025-01-15",
    })
    assert resp.status_code == 200

    resp = client.get("/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["name"] == "Pikachu"
    assert data["items"][0]["pnl_hkd"] == 2000.0
    assert data["total_invested"] == 8000.0


def test_delete_portfolio_item(client, db):
    card = _seed_card_with_price(db, name="Raichu")
    resp = client.post("/portfolio", json={
        "card_id": str(card.id),
        "purchase_price_hkd": 5000.0,
        "purchased_at": "2025-03-01",
    })
    item_id = resp.json()["id"]
    del_resp = client.delete(f"/portfolio/{item_id}")
    assert del_resp.status_code == 200
    remaining_ids = [i["id"] for i in client.get("/portfolio").json()["items"]]
    assert item_id not in remaining_ids
