"""
Backfill PSA 10 price history from PriceCharting for all cards in the DB.
Uses Playwright to load each card's individual page and extract Highcharts data.
Run once: python backfill_history.py
"""
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from playwright.sync_api import sync_playwright
from backend.models import Card, PriceSnapshot
from backend.scrapers.fx import get_usd_to_hkd

SET_SLUGS = {
    "Base Set":       "pokemon-base-set",
    "Jungle":         "pokemon-jungle",
    "Fossil":         "pokemon-fossil",
    "Team Rocket":    "pokemon-team-rocket",
    "Neo Genesis":    "pokemon-neo-genesis",
    "Neo Revelation": "pokemon-neo-revelation",
    "Neo Discovery":  "pokemon-neo-discovery",
    "Neo Destiny":    "pokemon-neo-destiny",
    "Gym Heroes":     "pokemon-gym-heroes",
    "Gym Challenge":  "pokemon-gym-challenge",
}


def make_pc_url(card: Card) -> str | None:
    set_slug = SET_SLUGS.get(card.set_name)
    if not set_slug:
        return None
    number = (card.card_number or "").split("/")[0]
    name_slug = re.sub(r"[^a-z0-9]+", "-", card.name.lower()).strip("-")
    slug = f"{name_slug}-{number}" if number else name_slug
    return f"https://www.pricecharting.com/game/{set_slug}/{slug}"


def fetch_psa10_history(url: str, page) -> list[tuple[datetime, float]]:
    """Load PriceCharting page, extract PSA 10 series from Highcharts."""
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
    except Exception as e:
        print(f"  Page load error: {e}")
        return []

    try:
        series = page.evaluate("""
            () => {
                if (typeof Highcharts === 'undefined') return null;
                const chart = Highcharts.charts.find(c => c);
                if (!chart) return null;
                return chart.series.map(s => ({
                    name: s.name,
                    data: s.data
                        .filter(p => p !== null && p !== undefined && p.y !== null && p.y !== undefined)
                        .map(p => [p.x, p.y])
                }));
            }
        """)
    except Exception as e:
        print(f"  Highcharts eval error: {e}")
        return []

    if not series:
        return []

    psa10 = next((s for s in series if s["name"] == "PSA 10"), None)
    if not psa10:
        print(f"  No PSA 10 series found. Available: {[s['name'] for s in series]}")
        return []

    points = []
    for x, y in psa10["data"]:
        if y and y > 0:
            dt = datetime.fromtimestamp(x / 1000, tz=timezone.utc)
            points.append((dt, float(y)))
    return points


def run_backfill(database_url: str) -> None:
    engine = create_engine(database_url)

    try:
        fx_rate = get_usd_to_hkd()
        print(f"Live FX rate: 1 USD = {fx_rate:.4f} HKD")
    except Exception as e:
        fx_rate = 7.8
        print(f"FX fetch failed ({e}), using fallback rate {fx_rate}")

    with Session(engine) as session:
        cards = session.query(Card).all()
        print(f"Found {len(cards)} cards to backfill.\n")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            bpage = context.new_page()

            for card in cards:
                url = make_pc_url(card)
                if not url:
                    print(f"  Skipping {card.name} — no set slug for '{card.set_name}'")
                    continue

                print(f"Fetching {card.name} ({card.set_name}) ...")
                print(f"  URL: {url}")
                points = fetch_psa10_history(url, bpage)
                print(f"  Found {len(points)} PSA 10 data points")

                if not points:
                    continue

                existing_ts = {
                    s.scraped_at.replace(tzinfo=timezone.utc) if s.scraped_at.tzinfo is None else s.scraped_at
                    for s in card.snapshots
                    if s.pricecharting_price_usd is not None
                }

                inserted = 0
                for dt, price_usd in points:
                    if dt in existing_ts:
                        continue
                    snap = PriceSnapshot(
                        card_id=card.id,
                        pricecharting_price_usd=Decimal(str(round(price_usd, 2))),
                        pricecharting_price_hkd=Decimal(str(round(price_usd * fx_rate, 2))),
                        usd_to_hkd_rate=Decimal(str(round(fx_rate, 4))),
                        scraped_at=dt,
                    )
                    session.add(snap)
                    inserted += 1

                session.flush()
                print(f"  Inserted {inserted} new snapshots")

            browser.close()

        session.commit()
        print("\nBackfill complete.")


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("Set DATABASE_URL before running this script.")
    run_backfill(db_url)
