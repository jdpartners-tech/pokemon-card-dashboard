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
import requests as _requests

from backend.models import Card, PriceSnapshot
from backend.scrapers.pricecharting import fetch_product_page_data

SNKRDUNK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://snkrdunk.com/",
}


def fetch_snkrdunk_psa10_usd(snkrdunk_id: str) -> float | None:
    """Fetch current PSA 10 lowest asking price in USD from SNKRDunk product API."""
    try:
        url = f"https://snkrdunk.com/en/v1/trading-cards/{snkrdunk_id}/min-prices-by-conditions"
        r = _requests.get(url, headers=SNKRDUNK_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        for cp in r.json().get("conditionPrices", []):
            if cp.get("conditionName") == "PSA 10":
                price = cp.get("minPrice")
                return float(price) if price else None
    except Exception as e:
        logger.debug(f"SNKRDunk fetch failed (id={snkrdunk_id}): {e}")
    return None

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
            text("""SELECT DISTINCT card_id FROM price_snapshots
                    WHERE scraped_at::date = :today
                    AND (pricecharting_price_hkd IS NOT NULL OR snkrdunk_price_hkd IS NOT NULL)"""),
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

    all_scrapeable = db.query(Card).filter(
        (Card.pricecharting_url.isnot(None)) | (Card.snkrdunk_id.isnot(None))
    ).all()
    todo = [c for c in all_scrapeable if str(c.id) not in already_done]
    logger.info(f"To scrape: {len(todo)} / {len(all_scrapeable)} cards")

    fixed = failed = 0
    for i, card in enumerate(todo, 1):
        pc_price_usd = None
        snkr_price_usd = None
        image_url = None

        if card.pricecharting_url:
            pc_price_usd, image_url = fetch_product_page_data(card.pricecharting_url)

        if card.snkrdunk_id:
            snkr_price_usd = fetch_snkrdunk_psa10_usd(card.snkrdunk_id)
            time.sleep(0.3)

        if pc_price_usd or snkr_price_usd:
            snap = PriceSnapshot(
                card_id=card.id,
                pricecharting_price_usd=Decimal(str(round(pc_price_usd, 2))) if pc_price_usd else None,
                pricecharting_price_hkd=Decimal(str(round(pc_price_usd * fx, 2))) if pc_price_usd else None,
                snkrdunk_price_hkd=Decimal(str(round(snkr_price_usd * fx, 2))) if snkr_price_usd else None,
                usd_to_hkd_rate=Decimal(str(round(fx, 4))),
            )
            db.add(snap)
            fixed += 1
            pc_str = f"PC=${pc_price_usd:.2f}" if pc_price_usd else "PC=—"
            snkr_str = f"SNKR=${snkr_price_usd:.2f}" if snkr_price_usd else ""
            logger.info(f"[{i}/{len(todo)}] {card.name}: {pc_str} {snkr_str} → HK${(pc_price_usd or snkr_price_usd or 0) * fx:.2f}")
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
    logger.info(f"=== Done — {fixed} snapshots written, {failed} failed ===")


if __name__ == "__main__":
    run()
