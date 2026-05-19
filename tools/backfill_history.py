"""
Backfill monthly PSA 10 price history from PriceCharting for all cards.

PriceCharting embeds price history in VGPC.chart_data.manualonly on each
product page — monthly data points going back to Dec 2020.

This script:
  1. Fetches each card's product page
  2. Extracts the manualonly chart series (PSA 10 prices, in cents USD)
  3. Inserts backdated PriceSnapshots for any month not already covered

Safe to re-run: skips cards/months where a snapshot already exists.

Usage:
    python tools/backfill_history.py
"""

import os
import re
import sys
import time
import json
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from backend.models import Card, PriceSnapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.")
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

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
        logger.warning(f"Could not fetch live FX rate ({e}), using {FX_FALLBACK}")
        return FX_FALLBACK


def get_existing_months(engine) -> dict[str, set[str]]:
    """Return {card_id_str: set of 'YYYY-MM' strings} for all existing snapshots."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT card_id::text, to_char(scraped_at, 'YYYY-MM') FROM price_snapshots WHERE pricecharting_price_hkd IS NOT NULL")
        ).fetchall()
    result: dict[str, set[str]] = {}
    for card_id, ym in rows:
        result.setdefault(card_id, set()).add(ym)
    return result


def fetch_chart_history(url: str) -> list[tuple[datetime, float]]:
    """
    Fetch a PriceCharting product page and return list of (date, price_usd) from
    the manualonly (PSA 10) chart series. Skips zero-price entries.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code in (403, 404):
            return []
        r.raise_for_status()

        m = re.search(r"VGPC\.chart_data\s*=\s*(\{.*?\});", r.text, re.DOTALL)
        if not m:
            return []

        data = json.loads(m.group(1))
        series = data.get("manualonly", [])

        points = []
        for ts_ms, price_cents in series:
            if not price_cents or price_cents <= 0:
                continue
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            price_usd = price_cents / 100.0
            points.append((dt, price_usd))
        return points
    except Exception as e:
        logger.debug(f"Chart fetch failed ({url}): {e}")
        return []


def run():
    engine = make_engine()
    fx = get_fx_rate()

    existing_months = get_existing_months(engine)
    logger.info(f"Loaded existing snapshot months for {len(existing_months)} cards")

    Session = sessionmaker(bind=engine)
    db = Session()

    cards = db.query(Card).filter(Card.pricecharting_url.isnot(None)).all()
    logger.info(f"Cards to process: {len(cards)}")

    inserted = skipped_cards = failed = 0
    batch_inserts = 0

    for i, card in enumerate(cards, 1):
        card_id_str = str(card.id)
        existing = existing_months.get(card_id_str, set())

        history = fetch_chart_history(card.pricecharting_url)
        if not history:
            failed += 1
            logger.warning(f"[{i}/{len(cards)}] {card.name}: no chart data")
            time.sleep(0.5)
            continue

        new_points = 0
        for dt, price_usd in history:
            ym = dt.strftime("%Y-%m")
            if ym in existing:
                continue  # already have data for this month
            snap = PriceSnapshot(
                card_id=card.id,
                pricecharting_price_usd=Decimal(str(round(price_usd, 2))),
                pricecharting_price_hkd=Decimal(str(round(price_usd * fx, 2))),
                usd_to_hkd_rate=Decimal(str(round(fx, 4))),
                scraped_at=dt,
            )
            db.add(snap)
            existing.add(ym)  # prevent double-insert within same run
            new_points += 1
            batch_inserts += 1

        inserted += new_points
        if new_points == 0:
            skipped_cards += 1

        logger.info(f"[{i}/{len(cards)}] {card.name}: +{new_points} months ({len(history)} total in chart)")

        # Commit every 25 cards
        if i % 25 == 0:
            for attempt in range(3):
                try:
                    db.commit()
                    logger.info(f"  → committed at card {i} ({inserted} snapshots so far)")
                    break
                except OperationalError:
                    logger.warning(f"DB connection lost, reconnecting (attempt {attempt+1})...")
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
    logger.info(f"Done — {inserted} historical snapshots inserted, {skipped_cards} cards already fully covered, {failed} failed")


if __name__ == "__main__":
    run()
