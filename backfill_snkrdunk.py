"""
Backfill PSA 10 price history from Snkrdunk for all cards in the DB.

Phase 1: Scrape listing pages to collect (card, product_url) pairs.
Phase 2: Visit each product page, intercept chart API responses, extract history.
Phase 3: Match results to DB cards and insert historical PriceSnapshot rows.

Run once: python backfill_snkrdunk.py
"""
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.models import Card, PriceSnapshot
from backend.scrapers.snkrdunk_history import collect_product_urls, fetch_psa10_history_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_backfill(database_url: str) -> None:
    engine = create_engine(database_url)

    # Phase 1: collect (card_data, product_url) from listing pages
    logger.info("Phase 1: scraping Snkrdunk listing pages for product URLs...")
    listing_results = collect_product_urls(max_pages=20)
    if not listing_results:
        logger.error("No product URLs collected — Snkrdunk scraper may be broken. Aborting.")
        return

    # Build snkrdunk_id → product_url mapping (deduplicate by snkrdunk_id)
    id_to_url: dict[str, str] = {}
    for card, url in listing_results:
        if card.snkrdunk_id and url:
            id_to_url[card.snkrdunk_id] = url

    logger.info(f"Phase 1 complete: {len(id_to_url)} unique cards with product URLs")

    # Phase 2: fetch historical data for each product URL
    logger.info("Phase 2: fetching price history from product pages...")
    product_urls = list(id_to_url.values())
    url_to_history = fetch_psa10_history_batch(product_urls)

    # Invert: snkrdunk_id → history
    snkrdunk_id_to_history: dict[str, list] = {}
    for snkrdunk_id, url in id_to_url.items():
        history = url_to_history.get(url, [])
        if history:
            snkrdunk_id_to_history[snkrdunk_id] = history

    logger.info(f"Phase 2 complete: got history for {len(snkrdunk_id_to_history)} cards")

    if not snkrdunk_id_to_history:
        logger.warning("No history data extracted. Check scraper logs above for clues about Snkrdunk's API format.")
        return

    # Phase 3: match to DB cards and insert snapshots
    logger.info("Phase 3: inserting historical snapshots into DB...")
    with Session(engine) as session:
        total_inserted = 0

        for snkrdunk_id, history in snkrdunk_id_to_history.items():
            card = session.query(Card).filter(Card.snkrdunk_id == snkrdunk_id).first()
            if not card:
                logger.warning(f"No DB card found for snkrdunk_id={snkrdunk_id}, skipping")
                continue

            # Collect existing Snkrdunk snapshot timestamps to avoid duplicates
            existing_ts = {
                s.scraped_at.replace(tzinfo=timezone.utc) if s.scraped_at.tzinfo is None else s.scraped_at
                for s in card.snapshots
                if s.snkrdunk_price_hkd is not None
            }

            inserted = 0
            for dt, price_hkd in history:
                if dt in existing_ts:
                    continue
                snap = PriceSnapshot(
                    card_id=card.id,
                    snkrdunk_price_hkd=Decimal(str(round(price_hkd, 2))),
                    scraped_at=dt,
                )
                session.add(snap)
                inserted += 1

            if inserted:
                session.flush()
                logger.info(f"  {card.name} ({card.set_name}): inserted {inserted} snapshots")
                total_inserted += inserted

        session.commit()
        logger.info(f"\nSnkrdunk backfill complete: {total_inserted} total snapshots inserted.")


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("Set DATABASE_URL before running this script.")
    run_backfill(db_url)
