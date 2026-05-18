"""
Run this script from your LOCAL machine to fix PriceCharting PSA 10 prices.

Render's server IP is blocked by Cloudflare; your home IP is not.
This script connects directly to the Render PostgreSQL database and updates prices.

Usage:
    1. Copy your Render DATABASE_URL into a .env file at the project root:
           DATABASE_URL=postgresql://user:pass@host/dbname
       (Find it in Render dashboard → pokemon-dashboard-api → Environment)
    2. From the project root, run:
           pip install sqlalchemy psycopg2-binary beautifulsoup4 requests python-dotenv
           python tools/fix_prices_local.py

It will scrape PSA 10 prices for all cards and insert fresh PriceSnapshots.
"""

import os
import sys
import time
import logging
from decimal import Decimal
from pathlib import Path

# Allow importing backend modules from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Add it to .env at the project root.")
    sys.exit(1)

# Patch DATABASE_URL into the backend config before importing models
os.environ["DATABASE_URL"] = DATABASE_URL

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Card, PriceSnapshot
from backend.scrapers.pricecharting import fetch_product_page_data
from backend.scheduler import _fix_pc_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FX_RATE = 7.80  # USD → HKD fallback; edit if needed


def get_fx_rate() -> float:
    try:
        from backend.scrapers.fx import get_usd_to_hkd
        rate = get_usd_to_hkd()
        logger.info(f"Live FX rate: {rate}")
        return rate
    except Exception as e:
        logger.warning(f"Could not fetch live FX rate ({e}), using {FX_RATE}")
        return FX_RATE


def run():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    fx = get_fx_rate()

    cards = db.query(Card).filter(Card.pricecharting_url.isnot(None)).all()
    logger.info(f"Fixing PSA 10 prices for {len(cards)} cards (FX: {fx})")

    fixed = 0
    failed = 0
    for i, card in enumerate(cards, 1):
        url = _fix_pc_url(card.pricecharting_url)
        if url != card.pricecharting_url:
            card.pricecharting_url = url

        price_usd, image_url = fetch_product_page_data(url)

        if price_usd and price_usd > 0:
            snap = PriceSnapshot(
                card_id=card.id,
                pricecharting_price_usd=Decimal(str(round(price_usd, 2))),
                pricecharting_price_hkd=Decimal(str(round(price_usd * fx, 2))),
                usd_to_hkd_rate=Decimal(str(round(fx, 4))),
            )
            db.add(snap)
            fixed += 1
            logger.info(f"[{i}/{len(cards)}] {card.name}: ${price_usd:.2f} / HK${price_usd * fx:.2f}")
        else:
            failed += 1
            logger.warning(f"[{i}/{len(cards)}] {card.name}: no price found ({url})")

        if image_url and not card.image_url:
            card.image_url = image_url

        if i % 50 == 0:
            db.commit()
            logger.info(f"  → committed {i} cards so far")

        time.sleep(0.5)  # polite rate limit

    db.commit()
    db.close()
    logger.info(f"Done — {fixed} prices updated, {failed} failed")


if __name__ == "__main__":
    run()
