"""
Daily PSA 10 price scraper — run this once per day to build price history.

Scrapes current PriceCharting PSA 10 prices for all cards and inserts fresh
PriceSnapshots. Cards already updated today (UTC) are skipped.

Recommended: add to Windows Task Scheduler to run automatically at 9am daily.
    Action: python C:\path\to\pokemon-card-dashboard\tools\daily_scrape.py
    Start in: C:\path\to\pokemon-card-dashboard

Usage:
    python tools/daily_scrape.py
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / "daily_scrape.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

FX_FALLBACK = 7.83


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


def get_fx_rate():
    try:
        from backend.scrapers.fx import get_usd_to_hkd
        rate = get_usd_to_hkd()
        logger.info(f"Live FX rate: {rate}")
        return rate
    except Exception as e:
        logger.warning(f"FX fetch failed ({e}), using {FX_FALLBACK}")
        return FX_FALLBACK


def get_already_done(engine) -> set[str]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT card_id FROM price_snapshots WHERE scraped_at::date = :today AND pricecharting_price_hkd IS NOT NULL"),
            {"today": today},
        ).fetchall()
    return {str(r[0]) for r in rows}


def run():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info(f"=== Daily scrape starting — {today} UTC ===")

    engine = make_engine()
    fx = get_fx_rate()
    already_done = get_already_done(engine)
    logger.info(f"Already scraped today: {len(already_done)} cards")

    Session = sessionmaker(bind=engine)
    db = Session()

    cards = db.query(Card).filter(Card.pricecharting_url.isnot(None)).all()
    todo = [c for c in cards if str(c.id) not in already_done]
    logger.info(f"To scrape: {len(todo)} / {len(cards)} cards")

    fixed = failed = 0
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
            logger.info(f"[{i}/{len(todo)}] {card.name}: ${price_usd:.2f} → HK${price_usd * fx:.2f}")
        else:
            failed += 1
            logger.warning(f"[{i}/{len(todo)}] {card.name}: no price")

        if image_url and not card.image_url:
            card.image_url = image_url

        if i % 25 == 0:
            for attempt in range(3):
                try:
                    db.commit()
                    logger.info(f"  → committed at {i} ({fixed} prices)")
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
    logger.info(f"=== Done — {fixed} new prices, {failed} failed ===")


if __name__ == "__main__":
    run()
