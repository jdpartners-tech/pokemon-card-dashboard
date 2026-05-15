import uuid
from backend.models import Card, WatchlistItem


def _seed_card(db):
    card = Card(id=uuid.uuid4(), name="Mewtwo", set_name="Base Set", card_number="10/102")
    db.add(card)
    db.commit()
    return card


def test_get_watchlist_empty(client):
    resp = client.get("/watchlist")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_to_watchlist(client, db):
    card = _seed_card(db)
    resp = client.post("/watchlist", json={"card_id": str(card.id)})
    assert resp.status_code == 200

    resp2 = client.get("/watchlist")
    ids = [c["id"] for c in resp2.json()]
    assert str(card.id) in ids


def test_add_duplicate_watchlist_returns_400(client, db):
    card = _seed_card(db)
    client.post("/watchlist", json={"card_id": str(card.id)})
    resp = client.post("/watchlist", json={"card_id": str(card.id)})
    assert resp.status_code == 400


def test_delete_from_watchlist(client, db):
    card = _seed_card(db)
    client.post("/watchlist", json={"card_id": str(card.id)})
    resp = client.delete(f"/watchlist/{card.id}")
    assert resp.status_code == 200
    resp2 = client.get("/watchlist")
    ids = [c["id"] for c in resp2.json()]
    assert str(card.id) not in ids
