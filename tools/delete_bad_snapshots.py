"""
Delete the corrupt May 16 2026 Grade 9 price snapshots.

Those snapshots used PriceCharting's #graded_price (Grade 9) instead of
#manual_only_price (PSA 10). Run this AFTER fix_prices_local.py has
successfully updated all cards with correct PSA 10 prices.

Usage:
    python tools/delete_bad_snapshots.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.")
    sys.exit(1)


def run():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Preview first
        count = conn.execute(
            text("SELECT COUNT(*) FROM price_snapshots WHERE scraped_at::date = '2026-05-16'")
        ).scalar()
        print(f"Snapshots from 2026-05-16 (Grade 9 bad data): {count}")

        if count == 0:
            print("Nothing to delete.")
            return

        confirm = input(f"Delete {count} snapshots from 2026-05-16? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

        result = conn.execute(
            text("DELETE FROM price_snapshots WHERE scraped_at::date = '2026-05-16'")
        )
        conn.commit()
        print(f"Deleted {result.rowcount} snapshots.")

        # Verify remaining
        remaining = conn.execute(
            text("SELECT scraped_at::date as d, COUNT(*) FROM price_snapshots GROUP BY d ORDER BY d DESC LIMIT 5")
        ).fetchall()
        print("\nRemaining snapshots by date:")
        for row in remaining:
            print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    run()
