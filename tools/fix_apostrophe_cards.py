"""
Fix PriceCharting URLs for cards whose names contain apostrophes.

The original slug builder converted apostrophes to hyphens (e.g. "Blaine's" →
"blaine-s-") but PriceCharting URLs use no hyphen (e.g. "blaines-"). This fixes
all 156 affected cards: updates the stored URL and re-scrapes the PSA 10 price.

Run AFTER fix_prices_local.py has completed.

Usage:
    python tools/fix_apostrophe_cards.py
"""

import os
import re
import sys
import time
import logging
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.")
    sys.exit(1)

os.environ["DATABASE_URL"] = DATABASE_URL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from backend.models import Card, PriceSnapshot
from backend.scrapers.pricecharting import fetch_product_page_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FX_FALLBACK = 7.83

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


def make_engine():
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=60,
        connect_args={
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "connect_timeout": 10,
        },
    )


def build_correct_url(card) -> str | None:
    set_slug = SET_SLUG_MAP.get(card.set_name)
    if not set_slug:
        return None
    num_slug = card.card_number.split("/")[0] if card.card_number else ""
    # Remove apostrophes before slugifying — PriceCharting omits them entirely
    clean_name = card.name.replace("'", "")
    name_slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
    slug = f"{name_slug}-{num_slug}" if num_slug else name_slug
    return f"https://www.pricecharting.com/game/{set_slug}/{slug}"


def get_fx_rate():
    try:
        from backend.scrapers.fx import get_usd_to_hkd
        rate = get_usd_to_hkd()
        logger.info(f"Live FX rate: {rate}")
        return rate
    except Exception as e:
        logger.warning(f"FX fetch failed ({e}), using {FX_FALLBACK}")
        return FX_FALLBACK


def run():
    engine = make_engine()
    fx = get_fx_rate()

    Session = sessionmaker(bind=engine)
    db = Session()

    # Find all cards with apostrophes in their names
    cards = [c for c in db.query(Card).all() if "'" in c.name]
    logger.info(f"Cards with apostrophes in name: {len(cards)}")

    # Step 1: Fix URLs
    url_fixed = 0
    for card in cards:
        correct_url = build_correct_url(card)
        if correct_url and correct_url != card.pricecharting_url:
            old = card.pricecharting_url
            card.pricecharting_url = correct_url
            url_fixed += 1
            logger.info(f"URL fix: {card.name}")
            logger.info(f"  old: {old}")
            logger.info(f"  new: {correct_url}")
    db.commit()
    logger.info(f"Fixed URLs for {url_fixed} cards")

    # Step 2: Scrape current PSA 10 price for all apostrophe cards
    fixed = failed = 0
    for i, card in enumerate(cards, 1):
        if not card.pricecharting_url:
            failed += 1
            continue

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
            logger.info(f"[{i}/{len(cards)}] {card.name}: ${price_usd:.2f} / HK${price_usd * fx:.2f}")
        else:
            failed += 1
            logger.warning(f"[{i}/{len(cards)}] {card.name}: no price ({card.pricecharting_url})")

        if image_url and not card.image_url:
            card.image_url = image_url

        if i % 25 == 0:
            for attempt in range(3):
                try:
                    db.commit()
                    logger.info(f"  → committed at {i} ({fixed} prices so far)")
                    break
                except OperationalError:
                    logger.warning(f"DB reconnect attempt {attempt+1}...")
                    db.close()
                    engine = make_engine()
                    Session = sessionmaker(bind=engine)
                    db = Session()
                    time.sleep(2)

        time.sleep(0.5)

    for attempt in range(3):
        try:
            db.commit()
            break
        except OperationalError:
            db.close()
            engine = make_engine()
            db = sessionmaker(bind=engine)()
            time.sleep(2)

    db.close()
    logger.info(f"Done — {fixed} prices added, {failed} failed/not found on PriceCharting")


if __name__ == "__main__":
    run()
