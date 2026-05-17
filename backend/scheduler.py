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

        pc_prices = _collect_pricecharting(db, fx_rate)
        snkr_prices = _collect_snkrdunk(db)

        all_card_ids = set(pc_prices) | set(snkr_prices)
        for card_id in all_card_ids:
            snap = PriceSnapshot(card_id=card_id)
            if card_id in pc_prices:
                usd, hkd = pc_prices[card_id]
                snap.pricecharting_price_usd = Decimal(str(usd))
                snap.pricecharting_price_hkd = Decimal(str(hkd))
                snap.usd_to_hkd_rate = Decimal(str(round(fx_rate, 4)))
            if card_id in snkr_prices:
                snap.snkrdunk_price_hkd = Decimal(str(snkr_prices[card_id]))
            db.add(snap)

        db.commit()
        logger.info(f"Scrape job complete: {len(all_card_ids)} cards updated")
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


def _collect_pricecharting(db, fx_rate: float) -> dict:
    """Scrape PriceCharting and return {card.id: (price_usd, price_hkd)}."""
    try:
        scraped = scrape_pricecharting()
    except Exception as e:
        logger.error(f"PriceCharting scrape failed: {e}")
        return {}

    prices = {}
    for item in scraped:
        try:
            card = _get_or_create_card(
                db,
                name=item.name,
                set_name=item.set_name,
                card_number=item.card_number,
                pricecharting_id=item.pricecharting_id,
            )
            price_hkd = item.psa10_price_hkd
            price_usd = round(price_hkd / fx_rate, 2) if fx_rate else 0.0
            prices[card.id] = (price_usd, price_hkd)
        except Exception as e:
            logger.warning(f"PC collect row failed ({item.name}): {e}")

    logger.info(f"PriceCharting: collected {len(prices)} cards")
    return prices


def _collect_snkrdunk(db) -> dict:
    """Scrape Snkrdunk and return {card.id: price_hkd}."""
    try:
        scraped = scrape_snkrdunk()
    except Exception as e:
        logger.error(f"Snkrdunk scrape failed: {e}")
        return {}

    prices = {}
    for item in scraped:
        try:
            card = _get_or_create_card(
                db,
                name=item.name,
                set_name=item.set_name,
                card_number=item.card_number,
                snkrdunk_id=item.snkrdunk_id,
            )
            prices[card.id] = item.psa10_price_hkd
        except Exception as e:
            logger.warning(f"Snkrdunk collect row failed ({item.name}): {e}")

    logger.info(f"Snkrdunk: collected {len(prices)} cards")
    return prices


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scrape_job, "interval", hours=6, id="scrape", replace_existing=True)
    return scheduler
