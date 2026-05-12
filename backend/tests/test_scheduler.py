from decimal import Decimal
from unittest.mock import patch, MagicMock
from backend.scheduler import run_scrape_job, _get_or_create_card, _ingest_pricecharting, _ingest_snkrdunk
from backend.scrapers.pricecharting import ScrapedCard as PCCard
from backend.scrapers.snkrdunk import ScrapedCard as SDCard
from backend.models import Card, PriceSnapshot


def test_get_or_create_card_creates_new(db):
    card = _get_or_create_card(db, name="Pikachu", set_name="Base Set", card_number="58/102", pricecharting_id="pc-pikachu")
    db.flush()
    assert card.id is not None
    assert card.name == "Pikachu"


def test_get_or_create_card_returns_existing(db):
    card1 = _get_or_create_card(db, name="Mewtwo", set_name="Base Set", card_number="10/102", pricecharting_id="pc-mewtwo")
    db.flush()
    card2 = _get_or_create_card(db, name="Mewtwo", set_name="Base Set", card_number="10/102", pricecharting_id="pc-mewtwo")
    assert card1.id == card2.id


def test_get_or_create_card_links_ids(db):
    # First ingested via pricecharting, then matched by name for snkrdunk
    card = _get_or_create_card(db, name="Blastoise", set_name="Base Set", card_number="2/102", pricecharting_id="pc-blastoise")
    db.flush()
    card2 = _get_or_create_card(db, name="Blastoise", set_name="Base Set", card_number="2/102", snkrdunk_id="sd-blastoise")
    assert card.id == card2.id
    assert card2.snkrdunk_id == "sd-blastoise"


def test_ingest_pricecharting_creates_snapshot(db):
    scraped = [PCCard(name="Venusaur", set_name="Base Set", card_number="15/102", pricecharting_id="pc-venu", psa10_price_usd=500.0)]
    with patch("backend.scheduler.scrape_pricecharting", return_value=scraped):
        _ingest_pricecharting(db, fx_rate=7.8)
    db.flush()
    card = db.query(Card).filter(Card.pricecharting_id == "pc-venu").first()
    snaps = db.query(PriceSnapshot).filter(PriceSnapshot.card_id == card.id).all()
    assert len(snaps) == 1
    assert snaps[0].pricecharting_price_usd == Decimal("500.0")
    assert snaps[0].pricecharting_price_hkd == Decimal("3900.0")


def test_ingest_snkrdunk_creates_snapshot(db):
    scraped = [SDCard(name="Charizard", set_name="Base Set", card_number="4/102", snkrdunk_id="sd-char", psa10_price_hkd=12000.0)]
    with patch("backend.scheduler.scrape_snkrdunk", return_value=scraped):
        _ingest_snkrdunk(db)
    db.flush()
    snaps = db.query(PriceSnapshot).filter(PriceSnapshot.snkrdunk_price_hkd.isnot(None)).all()
    assert len(snaps) >= 1
    assert snaps[-1].snkrdunk_price_hkd == Decimal("12000.0")


def test_run_scrape_job_handles_fx_failure(db):
    with patch("backend.scheduler.SessionLocal", return_value=db), \
         patch("backend.scheduler.get_usd_to_hkd", side_effect=Exception("timeout")), \
         patch("backend.scheduler.scrape_pricecharting") as mock_pc:
        run_scrape_job()
        mock_pc.assert_not_called()
