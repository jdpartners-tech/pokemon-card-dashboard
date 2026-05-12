import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from backend.scoring import score_cards, calculate_price_trend, calculate_arbitrage
from backend.models import Card, PriceSnapshot


def _card(name="Charizard"):
    c = Card()
    c.id = uuid.uuid4()
    c.name = name
    c.set_name = "Base Set"
    c.card_number = "4/102"
    return c


def _snap(snkr=None, pc_hkd=None, days_ago=0):
    s = PriceSnapshot()
    s.id = uuid.uuid4()
    s.snkrdunk_price_hkd = Decimal(str(snkr)) if snkr else None
    s.pricecharting_price_hkd = Decimal(str(pc_hkd)) if pc_hkd else None
    s.scraped_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return s


def test_trend_rising():
    snaps = [_snap(snkr=1000, days_ago=13), _snap(snkr=1200, days_ago=3)]
    trend = calculate_price_trend(snaps, days=7)
    assert trend is not None
    assert trend > 0


def test_trend_no_data_returns_none():
    assert calculate_price_trend([], days=7) is None


def test_arbitrage_gap():
    snaps = [_snap(snkr=5000, pc_hkd=4000, days_ago=0)]
    gap = calculate_arbitrage(snaps)
    assert gap == pytest.approx(1000.0)


def test_score_cards_returns_sorted_descending():
    card_a = _card("Charizard")
    card_b = _card("Pikachu")
    snaps_a = [_snap(snkr=5000, pc_hkd=4000, days_ago=10), _snap(snkr=6000, pc_hkd=5500, days_ago=1)]
    snaps_b = [_snap(snkr=100, pc_hkd=100, days_ago=1)]
    results = score_cards([(card_a, snaps_a), (card_b, snaps_b)])
    assert results[0]["card"].name == "Charizard"
    assert results[0]["score"] >= results[1]["score"]


def test_score_range():
    card = _card()
    snaps = [_snap(snkr=1000, pc_hkd=950, days_ago=0)]
    results = score_cards([(card, snaps)])
    assert 0 <= results[0]["score"] <= 100
