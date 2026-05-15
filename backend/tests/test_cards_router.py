import uuid
from decimal import Decimal
from datetime import datetime, timezone
from backend.models import Card, PriceSnapshot


def _seed_card(db, name="Charizard", set_name="Base Set"):
    card = Card(id=uuid.uuid4(), name=name, set_name=set_name, card_number="4/102")
    snap = PriceSnapshot(
        id=uuid.uuid4(),
        card_id=card.id,
        snkrdunk_price_hkd=Decimal("45000"),
        pricecharting_price_hkd=Decimal("42000"),
        usd_to_hkd_rate=Decimal("7.85"),
        scraped_at=datetime.now(timezone.utc),
    )
    db.add(card)
    db.add(snap)
    db.commit()
    return card


def test_get_cards_returns_list(client, db):
    _seed_card(db)
    resp = client.get("/cards")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "score" in data[0]
    assert "name" in data[0]


def test_get_cards_search_filter(client, db):
    _seed_card(db, name="Pikachu", set_name="Base Set")
    resp = client.get("/cards?search=Pikachu")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert all("Pikachu" in n for n in names)


def test_get_card_detail(client, db):
    card = _seed_card(db, name="Blastoise")
    resp = client.get(f"/cards/{card.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Blastoise"
    assert "history" in data
    assert len(data["history"]) >= 1


def test_get_card_not_found(client):
    resp = client.get(f"/cards/{uuid.uuid4()}")
    assert resp.status_code == 404
