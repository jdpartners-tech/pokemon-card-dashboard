"""
One-time script: import cards from Derek's Pokemon Card.xlsx into the DB.
- Bought  → cards + portfolio_items + price snapshot
- Wait    → cards + watchlist + price snapshot
"""
import uuid
import os
from datetime import date, datetime, timezone
import psycopg2
import psycopg2.extras
psycopg2.extras.register_uuid()
from dotenv import load_dotenv

load_dotenv()

TODAY = date(2026, 5, 23)
TODAY_TS = datetime(2026, 5, 23, 9, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Cards parsed from Excel (name, set_name, card_number, snkrdunk_url, price_hkd, status)
# Price = MIN(eBay, SNKRDunk) — used as current snapshot AND placeholder purchase price
# ---------------------------------------------------------------------------
CARDS = [
    # ── BOUGHT ──────────────────────────────────────────────────────────────
    {
        "name": "Pikachu With Grey Felt Hat (Van Gogh Promo)",
        "set_name": "SVP Promotional Cards",
        "card_number": "085",
        "snkrdunk_url": None,
        "price_hkd": 23848.22,
        "status": "Bought",
    },
    {
        "name": "MEGA Charizard X ex SAR",
        "set_name": "Inferno X",
        "card_number": "110/080",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KQR05PH0W9AMB0VQ20KF9W3J",
        "price_hkd": 9950.0,
        "status": "Bought",
    },
    {
        "name": "Kanazawa Pikachu",
        "set_name": "S-P Promotional Cards",
        "card_number": "147",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KQH2N5GRA2J8GGP84JD7KJP2",
        "price_hkd": 12836.0,
        "status": "Bought",
    },
    {
        "name": "Umbreon VMAX HR: SA",
        "set_name": "Eevee Heroes",
        "card_number": "095/069",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KQCZ8SFGM7MNW037QX12TD7V",
        "price_hkd": 42287.0,
        "status": "Bought",
    },
    {
        "name": "Gengar & Mimikyu GX SR: SA",
        "set_name": "Tag Bolt",
        "card_number": "103/095",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/93096",
        "price_hkd": 29883.0,
        "status": "Bought",
    },
    {
        "name": "Gengar VMAX: SA",
        "set_name": "Gengar VMAX High Class Deck",
        "card_number": "020/019",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/91178",
        "price_hkd": 22506.0,
        "status": "Bought",
    },
    {
        "name": "Mega Tokyo Pikachu",
        "set_name": "XY-P Promotional Cards",
        "card_number": "098/XY-P",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/91422",
        "price_hkd": 21506.0,
        "status": "Bought",
    },
    {
        "name": "Pikachu (Pokemon Stamp Box)",
        "set_name": "S-P Promotional Cards",
        "card_number": "227",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/91118",
        "price_hkd": 37510.0,
        "status": "Bought",
    },
    {
        "name": "Mew ex SAR",
        "set_name": "Shiny Treasure ex",
        "card_number": "347/190",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KRDV29GRVE56JFYA3F11PRPZ",
        "price_hkd": 7788.0,
        "status": "Bought",
    },
    # ── WATCHLIST ────────────────────────────────────────────────────────────
    {
        "name": "Charizard ex SAR",
        "set_name": "Ruler of the Black Flame",
        "card_number": "134/108",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KQR7AJR0398F9GZCNTNQRHTC",
        "price_hkd": 4975.0,
        "status": "Wait",
    },
    {
        "name": "Pikachu ex UR",
        "set_name": "Supercharged Breaker",
        "card_number": "136/106",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KPW0HBNGHK74PKNRCNTZAE0H",
        "price_hkd": 3101.0,
        "status": "Wait",
    },
    {
        "name": "Team Rocket's Mewtwo ex SAR",
        "set_name": "MEGA Dream ex",
        "card_number": "237/193",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KNEK8DF03GY56YSP1JZXE8EW",
        "price_hkd": 3234.0,
        "status": "Wait",
    },
    {
        "name": "Mew ex SAR",
        "set_name": "Pokemon Card 151",
        "card_number": "205/165",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KGDN63MG8GH04BP15S6XCATF",
        "price_hkd": 5671.0,
        "status": "Wait",
    },
    {
        "name": "Mew V SR: SA",
        "set_name": "Fusion Arts",
        "card_number": "106/100",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/used/listings/01KQEAJG88JHCR3K7ZTSSBKGX8",
        "price_hkd": 3483.0,
        "status": "Wait",
    },
    {
        "name": "Pikachu ex SAR Style",
        "set_name": "Battle Collection",
        "card_number": "764/742",
        "snkrdunk_url": "https://snkrdunk.com/en/trading-cards/737036",
        "price_hkd": 32484.0,
        "status": "Wait",
    },
]

# ---------------------------------------------------------------------------

def run():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    inserted_cards = 0
    inserted_portfolio = 0
    inserted_watchlist = 0
    inserted_snapshots = 0
    skipped = 0

    for c in CARDS:
        # Check if already exists (same name + set_name + card_number)
        cur.execute(
            "SELECT id FROM cards WHERE name=%s AND set_name=%s AND card_number=%s",
            (c["name"], c["set_name"], c["card_number"]),
        )
        existing = cur.fetchone()
        if existing:
            card_id = existing[0]
            print(f"  SKIP (exists): {c['name']} [{c['set_name']} {c['card_number']}]")
            skipped += 1
        else:
            card_id = uuid.uuid4()
            cur.execute(
                """INSERT INTO cards (id, name, set_name, card_number, snkrdunk_url, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (card_id, c["name"], c["set_name"], c["card_number"], c["snkrdunk_url"], TODAY_TS),
            )
            print(f"  CARD: {c['name']} [{c['set_name']} {c['card_number']}]")
            inserted_cards += 1

        # Price snapshot
        cur.execute(
            """INSERT INTO price_snapshots (id, card_id, snkrdunk_price_hkd, scraped_at)
               VALUES (%s, %s, %s, %s)""",
            (uuid.uuid4(), card_id, c["price_hkd"], TODAY_TS),
        )
        inserted_snapshots += 1

        if c["status"] == "Bought":
            cur.execute(
                """INSERT INTO portfolio_items (id, card_id, purchase_price_hkd, purchased_at, added_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (uuid.uuid4(), card_id, c["price_hkd"], TODAY, TODAY_TS),
            )
            inserted_portfolio += 1
        else:
            cur.execute(
                """INSERT INTO watchlist (id, card_id, added_at)
                   VALUES (%s, %s, %s)""",
                (uuid.uuid4(), card_id, TODAY_TS),
            )
            inserted_watchlist += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone:")
    print(f"  {inserted_cards} cards inserted, {skipped} skipped")
    print(f"  {inserted_snapshots} price snapshots")
    print(f"  {inserted_portfolio} portfolio items")
    print(f"  {inserted_watchlist} watchlist items")


if __name__ == "__main__":
    run()
