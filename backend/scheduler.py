import logging
from decimal import Decimal
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import SessionLocal
from backend.models import Card, PriceSnapshot
from backend.scrapers.fx import get_usd_to_hkd
from backend.scrapers.pricecharting import scrape_pricecharting
from backend.scrapers.snkrdunk import scrape_snkrdunk

logger = logging.getLogger(__name__)


def run_scrape_job():
    logger.info("Scrape job started")
    db = SessionLocal()
    try:
        try:
            fx_rate = get_usd_to_hkd()
        except Exception as e:
            logger.error(f"FX fetch failed: {e}")
            return

        _ingest_pricecharting(db, fx_rate)
        _ingest_snkrdunk(db)
        db.commit()
        logger.info("Scrape job complete")
    except Exception as e:
        db.rollback()
        logger.error(f"Scrape job failed: {e}")
    finally:
        db.close()


def _get_or_create_card(db, *, name, set_name, card_number, pricecharting_id=None, snkrdunk_id=None):
    if pricecharting_id:
        card = db.query(Card).filter(Card.pricecharting_id == pricecharting_id).first()
        if card:
            return card
    if snkrdunk_id:
        card = db.query(Card).filter(Card.snkrdunk_id == snkrdunk_id).first()
        if card:
            if pricecharting_id and not card.pricecharting_id:
                card.pricecharting_id = pricecharting_id
            return card
    # Match by name + set as a fallback to avoid duplicates
    card = db.query(Card).filter(Card.name == name, Card.set_name == set_name).first()
    if card:
        if pricecharting_id and not card.pricecharting_id:
            card.pricecharting_id = pricecharting_id
        if snkrdunk_id and not card.snkrdunk_id:
            card.snkrdunk_id = snkrdunk_id
        return card
    card = Card(
        name=name,
        set_name=set_name,
        card_number=card_number or "",
        pricecharting_id=pricecharting_id,
        snkrdunk_id=snkrdunk_id,
    )
    db.add(card)
    db.flush()
    return card


def _ingest_pricecharting(db, fx_rate: float):
    try:
        scraped = scrape_pricecharting()
    except Exception as e:
        logger.error(f"PriceCharting scrape failed: {e}")
        return

    for item in scraped:
        try:
            card = _get_or_create_card(
                db,
                name=item.name,
                set_name=item.set_name,
                card_number=item.card_number,
                pricecharting_id=item.pricecharting_id,
            )
            price_hkd = round(item.psa10_price_usd * fx_rate, 2)
            snap = PriceSnapshot(
                card_id=card.id,
                pricecharting_price_usd=Decimal(str(item.psa10_price_usd)),
                pricecharting_price_hkd=Decimal(str(price_hkd)),
                usd_to_hkd_rate=Decimal(str(round(fx_rate, 4))),
            )
            db.add(snap)
        except Exception as e:
            logger.warning(f"PC ingest row failed ({item.name}): {e}")

    logger.info(f"PriceCharting: ingested {len(scraped)} cards")


def _ingest_snkrdunk(db):
    try:
        scraped = scrape_snkrdunk()
    except Exception as e:
        logger.error(f"Snkrdunk scrape failed: {e}")
        return

    for item in scraped:
        try:
            card = _get_or_create_card(
                db,
                name=item.name,
                set_name=item.set_name,
                card_number=item.card_number,
                snkrdunk_id=item.snkrdunk_id,
            )
            snap = PriceSnapshot(
                card_id=card.id,
                snkrdunk_price_hkd=Decimal(str(item.psa10_price_hkd)),
            )
            db.add(snap)
        except Exception as e:
            logger.warning(f"Snkrdunk ingest row failed ({item.name}): {e}")

    logger.info(f"Snkrdunk: ingested {len(scraped)} cards")


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # Run once at startup, then every 6 hours
    scheduler.add_job(run_scrape_job, "interval", hours=6, id="scrape", replace_existing=True)
    return scheduler
