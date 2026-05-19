"""
Run this script from your LOCAL machine to fix PriceCharting PSA 10 prices.

Render's server IP is blocked by Cloudflare; your home IP is not.
This script:
  1. Reconstructs pricecharting_url for every card (none were saved to DB)
  2. Scrapes PSA 10 price from each card's product page
  3. Inserts fresh PriceSnapshots with correct prices

Usage:
    From the project root:
        python tools/fix_prices_local.py
    (Requires DATABASE_URL in .env at the project root)
"""

import os
import re
import sys
import time
import logging
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Add it to .env at the project root.")
    sys.exit(1)

os.environ["DATABASE_URL"] = DATABASE_URL

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Card, PriceSnapshot
from backend.scrapers.pricecharting import fetch_product_page_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FX_FALLBACK = 7.80

# PriceCharting set slug mapping for every set currently in the DB
SET_SLUG_MAP = {
    "Base Set":             "pokemon-base-set",
    "Base Set 2":           "pokemon-base-set-2",
    "Jungle":               "pokemon-jungle",
    "Fossil":               "pokemon-fossil",
    "Team Rocket":          "pokemon-team-rocket",
    "Gym Heroes":           "pokemon-gym-heroes",
    "Gym Challenge":        "pokemon-gym-challenge",
    "Neo Genesis":          "pokemon-neo-genesis",
    "Neo Discovery":        "pokemon-neo-discovery",
    "Neo Revelation":       "pokemon-neo-revelation",
    "Neo Destiny":          "pokemon-neo-destiny",
    "Legendary Collection": "pokemon-legendary-collection",
    "Expedition":           "pokemon-expedition",
}


def build_pc_url(card: Card) -> str | None:
    set_slug = SET_SLUG_MAP.get(card.set_name)
    if not set_slug:
        return None
    num_slug = card.card_number.split("/")[0] if card.card_number else ""
    name_slug = re.sub(r"[^a-z0-9]+", "-", card.name.lower()).strip("-")
    slug = f"{name_slug}-{num_slug}" if num_slug else name_slug
    return f"https://www.pricecharting.com/game/{set_slug}/{slug}"


def fix_broken_url(url: str) -> str:
    """Strip any extra path segment after the card slug (e.g. /ho-oh-7/64 → /ho-oh-7)."""
    parts = url.split("/game/", 1)
    if len(parts) != 2:
        return url
    base, rest = parts
    segments = rest.split("/")[:2]
    return f"{base}/game/{'/'.join(segments)}"


def get_fx_rate() -> float:
    try:
        from backend.scrapers.fx import get_usd_to_hkd
        rate = get_usd_to_hkd()
        logger.info(f"Live FX rate: {rate}")
        return rate
    except Exception as e:
        logger.warning(f"Could not fetch live FX rate ({e}), using {FX_FALLBACK}")
        return FX_FALLBACK


def run():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    fx = get_fx_rate()

    cards = db.query(Card).all()
    logger.info(f"Processing {len(cards)} cards")

    # Step 1: populate pricecharting_url for any card missing it
    url_updated = 0
    for card in cards:
        if not card.pricecharting_url:
            url = build_pc_url(card)
            if url:
                card.pricecharting_url = url
                url_updated += 1
        else:
            fixed = fix_broken_url(card.pricecharting_url)
            if fixed != card.pricecharting_url:
                card.pricecharting_url = fixed
    db.commit()
    logger.info(f"URLs populated/fixed for {url_updated} cards")

    # Step 2: scrape PSA 10 price from each product page
    cards_with_url = db.query(Card).filter(Card.pricecharting_url.isnot(None)).all()
    logger.info(f"Scraping PSA 10 prices for {len(cards_with_url)} cards (FX: {fx})")

    fixed = 0
    failed = 0
    for i, card in enumerate(cards_with_url, 1):
        price_usd, image_url = fetch_product_page_data(card.pricecharting_url)

        if price_usd and price_usd > 0:
            snap = PriceSnapshot(
                card_id=card.id,
                pricecharting_price_usd=Decimal(str(round(price_usd, 2))),
                pricecharting_price_hkd=Decimal(str(round(price_usd * fx, 2))),
                usd_to_hkd_rate=Decimal(str(round(fx, 4))),
            )
            db.add(snap)
            fixed += 1
            logger.info(f"[{i}/{len(cards_with_url)}] {card.name}: ${price_usd:.2f} / HK${price_usd * fx:.2f}")
        else:
            failed += 1
            logger.warning(f"[{i}/{len(cards_with_url)}] {card.name}: no price ({card.pricecharting_url})")

        if image_url and not card.image_url:
            card.image_url = image_url

        if i % 50 == 0:
            db.commit()
            logger.info(f"  → committed at card {i}")

        time.sleep(0.5)

    db.commit()
    db.close()
    logger.info(f"Done — {fixed} prices updated, {failed} failed/not found")


if __name__ == "__main__":
    run()
