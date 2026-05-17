from decimal import Decimal
from unittest.mock import patch
from backend.scheduler import run_scrape_job, _get_or_create_card, _collect_pricecharting, _collect_snkrdunk
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
    card = _get_or_create_card(db, name="Blastoise", set_name="Base Set", card_number="2/102", pricecharting_id="pc-blastoise")
    db.flush()
    card2 = _get_or_create_card(db, name="Blastoise", set_name="Base Set", card_number="2/102", snkrdunk_id="sd-blastoise")
    assert card.id == card2.id
    assert card2.snkrdunk_id == "sd-blastoise"


def test_collect_pricecharting_returns_price_dict(db):
    scraped = [PCCard(name="Venusaur", set_name="Base Set", card_number="15/102", pricecharting_id="pc-venu", psa10_price_usd=500.0)]
    with patch("backend.scheduler.scrape_pricecharting", return_value=scraped):
        prices = _collect_pricecharting(db, fx_rate=7.8)
    db.flush()
    card = db.query(Card).filter(Card.pricecharting_id == "pc-venu").first()
    assert card is not None
    assert card.id in prices
    usd, hkd = prices[card.id]
    assert usd == 500.0
    assert hkd == 3900.0


def test_collect_snkrdunk_returns_price_dict(db):
    scraped = [SDCard(name="Charizard", set_name="Base Set", card_number="4/102", snkrdunk_id="sd-char", psa10_price_hkd=12000.0)]
    with patch("backend.scheduler.scrape_snkrdunk", return_value=scraped):
        prices = _collect_snkrdunk(db)
    db.flush()
    card = db.query(Card).filter(Card.snkrdunk_id == "sd-char").first()
    assert card is not None
    assert prices[card.id] == 12000.0


def test_run_scrape_job_merges_prices_into_single_snapshot(db):
    """Both scrapers returning the same card writes ONE new snapshot with both prices filled."""
    pc_scraped = [PCCard(name="MergeTestCard", set_name="Test Set", card_number="1", pricecharting_id="pc-merge-test", psa10_price_usd=100.0)]
    sd_scraped = [SDCard(name="MergeTestCard", set_name="Test Set", card_number="1", snkrdunk_id="sd-merge-test", psa10_price_hkd=850.0)]

    with patch("backend.scheduler.SessionLocal", return_value=db), \
         patch("backend.scheduler.get_usd_to_hkd", return_value=7.8), \
         patch("backend.scheduler.scrape_pricecharting", return_value=pc_scraped), \
         patch("backend.scheduler.scrape_snkrdunk", return_value=sd_scraped):
        run_scrape_job()

    db.flush()
    card = db.query(Card).filter(Card.pricecharting_id == "pc-merge-test").first()
    assert card is not None
    snaps = db.query(PriceSnapshot).filter(PriceSnapshot.card_id == card.id).all()
    assert len(snaps) == 1, f"Expected 1 merged snapshot, got {len(snaps)}"
    assert snaps[0].pricecharting_price_hkd == Decimal("780.0")
    assert snaps[0].snkrdunk_price_hkd == Decimal("850.0")


def test_run_scrape_job_handles_fx_failure(db):
    with patch("backend.scheduler.SessionLocal", return_value=db), \
         patch("backend.scheduler.get_usd_to_hkd", side_effect=Exception("timeout")), \
         patch("backend.scheduler.scrape_pricecharting") as mock_pc:
        run_scrape_job()
        mock_pc.assert_not_called()
