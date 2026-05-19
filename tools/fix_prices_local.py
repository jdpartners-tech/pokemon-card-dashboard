"""
Run this script from your LOCAL machine to fix PriceCharting PSA 10 prices.

Render's server IP is blocked by Cloudflare; your home IP is not.
This script:
  1. Reconstructs pricecharting_url for any card missing it
  2. Scrapes PSA 10 price from each card's product page
  3. Inserts fresh PriceSnapshots — skips cards already updated today

Usage:
    From the project root:
        python tools/fix_prices_local.py
    (Requires DATABASE_URL in .env at the project root)

Safe to re-run — skips cards that already have a fresh snapshot from today.
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
    print("ERROR: DATABASE_URL not set. Add it to .env at the project root.")
    sys.exit(1)

os.environ["DATABASE_URL"] = DATABASE_URL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from backend.models import Card, PriceSnapshot
from backend.scrapers.pricecharting import fetch_product_page_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FX_FALLBACK = 7.80

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
        pool_pre_ping=True,           # test connection before use
        pool_recycle=60,              # recycle connections every 60s
        connect_args={
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "connect_timeout": 10,
        },
    )


def build_pc_url(card):
    set_slug = SET_SLUG_MAP.get(card.set_name)
    if not set_slug:
        return None
    num_slug = card.card_number.split("/")[0] if card.card_number else ""
    name_slug = re.sub(r"[^a-z0-9]+", "-", card.name.lower()).strip("-")
    slug = f"{name_slug}-{num_slug}" if num_slug else name_slug
    return f"https://www.pricecharting.com/game/{set_slug}/{slug}"


def fix_broken_url(url):
    parts = url.split("/game/", 1)
    if len(parts) != 2:
        return url
    base, rest = parts
    segments = rest.split("/")[:2]
    return f"{base}/game/{'/'.join(segments)}"


def get_fx_rate():
    try:
        from backend.scrapers.fx import get_usd_to_hkd
        rate = get_usd_to_hkd()
        logger.info(f"Live FX rate: {rate}")
        return rate
    except Exception as e:
        logger.warning(f"Could not fetch live FX rate ({e}), using {FX_FALLBACK}")
        return FX_FALLBACK


def get_already_done(engine):
    """Return set of card_ids that already have a snapshot from today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT card_id FROM price_snapshots WHERE scraped_at::date = :today AND pricecharting_price_hkd IS NOT NULL"),
            {"today": today},
        ).fetchall()
    return {str(r[0]) for r in rows}


def run():
    engine = make_engine()
    fx = get_fx_rate()

    # Find cards already processed in a previous run today — skip them
    already_done = get_already_done(engine)
    logger.info(f"Already updated today: {len(already_done)} cards — will skip these")

    Session = sessionmaker(bind=engine)
    db = Session()

    cards = db.query(Card).all()
    logger.info(f"Total cards: {len(cards)}")

    # Step 1: populate missing pricecharting_urls
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
    if url_updated:
        logger.info(f"URLs populated for {url_updated} cards")

    # Step 2: scrape prices — skip cards done today, reconnect on DB errors
    cards_with_url = [c for c in cards if c.pricecharting_url]
    todo = [c for c in cards_with_url if str(c.id) not in already_done]
    logger.info(f"Scraping prices for {len(todo)} remaining cards (FX: {fx})")

    fixed = skipped = failed = 0
    for i, card in enumerate(todo, 1):
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
            logger.info(f"[{i}/{len(todo)}] {card.name}: ${price_usd:.2f} / HK${price_usd * fx:.2f}")
        else:
            failed += 1
            logger.warning(f"[{i}/{len(todo)}] {card.name}: no price ({card.pricecharting_url})")

        if image_url and not card.image_url:
            card.image_url = image_url

        # Commit every 25 cards with reconnect on failure
        if i % 25 == 0:
            for attempt in range(3):
                try:
                    db.commit()
                    logger.info(f"  → committed at card {i} ({fixed} prices so far)")
                    break
                except OperationalError as e:
                    logger.warning(f"DB connection lost, reconnecting (attempt {attempt+1})...")
                    db.close()
                    engine = make_engine()
                    Session = sessionmaker(bind=engine)
                    db = Session()
                    time.sleep(2)

        time.sleep(0.5)

    # Final commit
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
    logger.info(f"Done — {fixed} new prices, {skipped} skipped, {failed} not found")


if __name__ == "__main__":
    run()
