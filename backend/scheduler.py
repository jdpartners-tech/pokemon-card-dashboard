import logging
import re
import time
from decimal import Decimal
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import SessionLocal
from backend.models import Card, PriceSnapshot
from backend.scrapers.fx import get_usd_to_hkd
from backend.scrapers.pokemontcg import fetch_card_image
from backend.scrapers.pricecharting import scrape_pricecharting, fetch_product_page_data
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
    # Fetch image + accent colour from pokemontcg.io (best-effort)
    try:
        image_url, accent_color = fetch_card_image(name, card_number)
        card.image_url = image_url
        card.accent_color = accent_color
    except Exception as e:
        logger.warning(f"Image fetch failed for {name!r}: {e}")
    return card


def _fix_pc_url(url: str) -> str:
    """Correct a broken PriceCharting URL like '/ho-oh-7/64' → '/ho-oh-7'."""
    # The path looks like /game/pokemon-set/card-slug where slug must not contain "/"
    parts = url.split("/game/", 1)
    if len(parts) != 2:
        return url
    base, rest = parts
    segments = rest.split("/")
    if len(segments) >= 2:
        # segments[0] = set slug, segments[1] = card slug, segments[2+] = broken fraction
        segments = segments[:2]
    return f"{base}/game/{'/'.join(segments)}"


def _collect_pricecharting(db, fx_rate: float) -> dict:
    """
    1. Use PriceCharting bulk API to discover cards and update metadata.
    2. Scrape current PSA 10 price from each card's product page (accurate).
    Returns {card.id: (price_usd, price_hkd)}.
    """
    try:
        scraped = scrape_pricecharting()
    except Exception as e:
        logger.error(f"PriceCharting scrape failed: {e}")
        return {}

    # Pass 1: upsert card metadata from API discovery
    for item in scraped:
        try:
            card = _get_or_create_card(
                db,
                name=item.name,
                set_name=item.set_name,
                card_number=item.card_number,
                pricecharting_id=item.pricecharting_id,
            )
            if item.pricecharting_url:
                card.pricecharting_url = item.pricecharting_url  # always overwrite to fix old broken URLs
            if item.psa_population is not None:
                card.psa_population = item.psa_population
            if item.sales_per_day is not None:
                card.sales_per_day = float(item.sales_per_day)
        except Exception as e:
            logger.warning(f"PC card upsert failed ({item.name}): {e}")

    db.flush()

    # Pass 2: scrape actual current prices from product pages
    prices = {}
    cards_with_url = db.query(Card).filter(Card.pricecharting_url.isnot(None)).all()
    logger.info(f"PriceCharting: fetching live prices for {len(cards_with_url)} product pages")

    for card in cards_with_url:
        url = _fix_pc_url(card.pricecharting_url)
        if url != card.pricecharting_url:
            card.pricecharting_url = url  # heal any broken URL still in DB
        try:
            price_usd, image_url = fetch_product_page_data(url)
            if price_usd and price_usd > 0:
                price_hkd = round(price_usd * fx_rate, 2)
                prices[card.id] = (price_usd, price_hkd)
            if image_url and not card.image_url:
                card.image_url = image_url
        except Exception as e:
            logger.warning(f"PC page fetch failed ({card.name}): {e}")
        time.sleep(0.4)  # ~2.5 req/sec — respectful of PriceCharting

    logger.info(f"PriceCharting: collected prices for {len(prices)} cards")
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
