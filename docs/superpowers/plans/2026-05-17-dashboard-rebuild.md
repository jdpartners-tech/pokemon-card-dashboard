# Dashboard Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Pokemon PSA 10 dashboard to show all cards across all sets, with real historical price data, PSA population, portfolio tracking, and a per-page Pokemon-art background theme.

**Architecture:** PriceCharting is the primary data source (API for card discovery + current prices; Playwright for historical prices, PSA pop, sales velocity). pokemontcg.io provides card images and type-based accent colours stored in the DB at card creation time. The frontend is three pages (Home, Card Detail, My Cards) each with a type-themed background image, dark overlay, and glassmorphism table rows.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, Playwright, APScheduler (backend) · Next.js 14, TypeScript, Tailwind CSS, SWR, Recharts (frontend)

---

## File Map

**Backend — modify:**
- `backend/models.py` — add 6 columns to `Card`, add `PortfolioItem`
- `backend/schemas.py` — rewrite `CardSummary`/`CardDetail`, add portfolio schemas
- `backend/scoring.py` — add `trend_1y`, `ath`, `pct_from_ath`, `trend_consistency`
- `backend/routers/cards.py` — new computed fields, filter only positive-trend cards
- `backend/scheduler.py` — trigger image lookup on card creation
- `backend/scrapers/pricecharting.py` — discover all sets, scrape pop + sales
- `backend/main.py` — register portfolio router

**Backend — create:**
- `backend/alembic/versions/0002_add_card_fields_and_portfolio.py`
- `backend/scrapers/pokemontcg.py` — image URL + accent colour lookup
- `backend/routers/portfolio.py` — GET/POST/DELETE /portfolio

**Frontend — modify:**
- `frontend/src/app/layout.tsx` — per-route background image, updated nav
- `frontend/src/app/page.tsx` — home page wired to new table
- `frontend/src/app/card/[id]/page.tsx` — full detail rebuild
- `frontend/src/components/CardTable.tsx` — new columns (pop, ATH, consistency, 1y)
- `frontend/src/lib/types.ts` — new fields + portfolio types
- `frontend/src/lib/api.ts` — new API calls

**Frontend — create:**
- `frontend/src/app/my-cards/page.tsx`
- `frontend/src/components/PortfolioTable.tsx`
- `frontend/src/components/AddCardModal.tsx`
- `frontend/src/components/PopChart.tsx`

---

## Phase 1: Database & Models

### Task 1: Migration — new card columns + portfolio_items table

**Files:**
- Create: `backend/alembic/versions/0002_add_card_fields_and_portfolio.py`

- [ ] **Step 1: Write the migration**

```python
# backend/alembic/versions/0002_add_card_fields_and_portfolio.py
"""add card fields and portfolio_items

Revision ID: 0002
Revises: 87fe7d11e185
Create Date: 2026-05-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: Union[str, None] = '87fe7d11e185'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cards', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('accent_color', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('snkrdunk_url', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('pricecharting_url', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('psa_population', sa.Integer(), nullable=True))
    op.add_column('cards', sa.Column('sales_per_day', sa.Numeric(8, 2), nullable=True))

    op.create_table(
        'portfolio_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('card_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purchase_price_hkd', sa.Numeric(12, 2), nullable=False),
        sa.Column('purchased_at', sa.Date(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('portfolio_items')
    for col in ['sales_per_day', 'psa_population', 'pricecharting_url',
                'snkrdunk_url', 'accent_color', 'image_url']:
        op.drop_column('cards', col)
```

- [ ] **Step 2: Run migration locally**

```bash
cd backend && alembic upgrade head
```

Expected: `Running upgrade 87fe7d11e185 -> 0002, add card fields and portfolio_items`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0002_add_card_fields_and_portfolio.py
git commit -m "feat: migration — add card image/pop/url fields and portfolio_items table"
```

---

### Task 2: Update SQLAlchemy models

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py  (new file)
from backend.models import Card, PortfolioItem

def test_card_has_new_fields():
    c = Card()
    assert hasattr(c, 'image_url')
    assert hasattr(c, 'accent_color')
    assert hasattr(c, 'snkrdunk_url')
    assert hasattr(c, 'pricecharting_url')
    assert hasattr(c, 'psa_population')
    assert hasattr(c, 'sales_per_day')

def test_portfolio_item_model_exists():
    p = PortfolioItem()
    assert hasattr(p, 'card_id')
    assert hasattr(p, 'purchase_price_hkd')
    assert hasattr(p, 'purchased_at')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest backend/tests/test_models.py -v
```

Expected: FAIL — `PortfolioItem` not found, Card missing attributes

- [ ] **Step 3: Update models.py**

```python
# backend/models.py  (full replacement)
import uuid
from sqlalchemy import Column, String, Numeric, DateTime, Integer, Date, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.database import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    set_name = Column(String, nullable=False)
    card_number = Column(String)
    snkrdunk_id = Column(String, unique=True)
    pricecharting_id = Column(String, unique=True)
    image_url = Column(String)
    accent_color = Column(String)
    snkrdunk_url = Column(String)
    pricecharting_url = Column(String)
    psa_population = Column(Integer)
    sales_per_day = Column(Numeric(8, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    snapshots = relationship("PriceSnapshot", back_populates="card",
                             order_by="PriceSnapshot.scraped_at",
                             cascade="all, delete-orphan", passive_deletes=True)
    watchlist_entry = relationship("WatchlistItem", back_populates="card",
                                   uselist=False, cascade="all, delete-orphan",
                                   passive_deletes=True)
    portfolio_items = relationship("PortfolioItem", back_populates="card",
                                   cascade="all, delete-orphan", passive_deletes=True)


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"),
                     nullable=False)
    snkrdunk_price_hkd = Column(Numeric(12, 2))
    pricecharting_price_usd = Column(Numeric(12, 2))
    pricecharting_price_hkd = Column(Numeric(12, 2))
    usd_to_hkd_rate = Column(Numeric(10, 4))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card", back_populates="snapshots")


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"),
                     nullable=False, unique=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card", back_populates="watchlist_entry")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"),
                     nullable=False)
    purchase_price_hkd = Column(Numeric(12, 2), nullable=False)
    purchased_at = Column(Date, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card", back_populates="portfolio_items")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest backend/tests/test_models.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat: add new Card fields and PortfolioItem model"
```

---

## Phase 2: Computed Metrics

### Task 3: Update scoring.py with new metrics

**Files:**
- Modify: `backend/scoring.py`
- Modify: `backend/tests/test_scoring.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_scoring.py`:

```python
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from backend.models import PriceSnapshot
from backend.scoring import (
    calculate_trend_vs_days_ago, calculate_ath,
    calculate_pct_from_ath, calculate_trend_consistency,
)

def _snap(days_ago: int, pc_hkd: float) -> PriceSnapshot:
    s = PriceSnapshot()
    s.scraped_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    s.pricecharting_price_hkd = Decimal(str(pc_hkd))
    s.snkrdunk_price_hkd = None
    return s

def test_trend_1y():
    snaps = [_snap(400, 10000), _snap(0, 15000)]
    result = calculate_trend_vs_days_ago(snaps, 365)
    assert result == pytest.approx(50.0, rel=0.01)

def test_ath_returns_highest_price():
    snaps = [_snap(200, 20000), _snap(100, 35000), _snap(0, 28000)]
    ath, ath_date = calculate_ath(snaps)
    assert ath == pytest.approx(35000.0)

def test_pct_from_ath_negative_when_below():
    snaps = [_snap(100, 35000), _snap(0, 28000)]
    result = calculate_pct_from_ath(snaps)
    assert result < 0
    assert result == pytest.approx(-20.0, rel=0.01)

def test_trend_consistency_all_up():
    # 4 weeks: each week end > week start
    snaps = [
        _snap(28, 10000), _snap(21, 11000),
        _snap(14, 12000), _snap(7, 13000), _snap(0, 14000),
    ]
    assert calculate_trend_consistency(snaps) == 4

def test_trend_consistency_mixed():
    snaps = [
        _snap(28, 10000), _snap(21, 9000),   # week 4: down
        _snap(14, 11000), _snap(7, 12000), _snap(0, 13000),  # weeks 1-3: up
    ]
    assert calculate_trend_consistency(snaps) == 3
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest backend/tests/test_scoring.py -v -k "test_ath or test_pct or test_consistency or test_trend_1y"
```

Expected: FAIL — functions not found

- [ ] **Step 3: Update scoring.py**

```python
# backend/scoring.py  (full replacement)
from datetime import datetime, timezone, timedelta
from typing import Optional


def _aware_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get_price(snap) -> Optional[float]:
    if snap.pricecharting_price_hkd:
        return float(snap.pricecharting_price_hkd)
    if snap.snkrdunk_price_hkd:
        return float(snap.snkrdunk_price_hkd)
    return None


def calculate_trend_vs_days_ago(snapshots, days: int) -> Optional[float]:
    if not snapshots:
        return None
    sorted_snaps = sorted(snapshots, key=lambda s: _aware_dt(s.scraped_at), reverse=True)
    latest_price = _get_price(sorted_snaps[0])
    if not latest_price:
        return None
    latest_dt = _aware_dt(sorted_snaps[0].scraped_at)
    cutoff = latest_dt - timedelta(days=days)
    old_snaps = [s for s in snapshots if _aware_dt(s.scraped_at) <= cutoff]
    if not old_snaps:
        return None
    old_snap = max(old_snaps, key=lambda s: _aware_dt(s.scraped_at))
    old_price = _get_price(old_snap)
    if not old_price or old_price == 0:
        return None
    return round((latest_price - old_price) / old_price * 100, 2)


def calculate_ath(snapshots) -> tuple[Optional[float], Optional[datetime]]:
    """Return (all-time-high price, date of that high)."""
    if not snapshots:
        return None, None
    best = max(snapshots, key=lambda s: _get_price(s) or 0)
    price = _get_price(best)
    if not price:
        return None, None
    return price, _aware_dt(best.scraped_at)


def calculate_pct_from_ath(snapshots) -> Optional[float]:
    """% difference between current price and all-time high. Negative = below ATH."""
    if not snapshots:
        return None
    sorted_snaps = sorted(snapshots, key=lambda s: _aware_dt(s.scraped_at), reverse=True)
    current = _get_price(sorted_snaps[0])
    if not current:
        return None
    ath, _ = calculate_ath(snapshots)
    if not ath or ath == 0:
        return None
    return round((current - ath) / ath * 100, 2)


def calculate_trend_consistency(snapshots) -> int:
    """Count of weeks (out of last 4) where price rose. Returns 0-4."""
    if not snapshots:
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    for week in range(1, 5):
        end_dt = now - timedelta(weeks=week - 1)
        start_dt = now - timedelta(weeks=week)
        end_snaps = [s for s in snapshots if _aware_dt(s.scraped_at) <= end_dt]
        start_snaps = [s for s in snapshots if _aware_dt(s.scraped_at) <= start_dt]
        if not end_snaps or not start_snaps:
            continue
        end_price = _get_price(max(end_snaps, key=lambda s: _aware_dt(s.scraped_at)))
        start_price = _get_price(max(start_snaps, key=lambda s: _aware_dt(s.scraped_at)))
        if end_price and start_price and end_price > start_price:
            count += 1
    return count
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_scoring.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/scoring.py backend/tests/test_scoring.py
git commit -m "feat: add trend_1y, ATH, pct_from_ath, trend_consistency metrics"
```

---

## Phase 3: Data Pipeline

### Task 4: pokemontcg.io image + accent colour scraper

**Files:**
- Create: `backend/scrapers/pokemontcg.py`
- Create: `backend/tests/test_pokemontcg.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_pokemontcg.py
from unittest.mock import patch, MagicMock
from backend.scrapers.pokemontcg import fetch_card_image, TYPE_COLORS

def test_type_colors_complete():
    for t in ["Fire", "Water", "Grass", "Psychic", "Lightning",
              "Fighting", "Dark", "Metal", "Dragon", "Fairy", "Colorless"]:
        assert t in TYPE_COLORS

def test_fetch_card_image_returns_url_and_color():
    mock_data = {
        "data": [{
            "images": {"small": "https://images.pokemontcg.io/base1/4.png"},
            "types": ["Fire"],
        }]
    }
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        url, color = fetch_card_image("Charizard", "4")
    assert url == "https://images.pokemontcg.io/base1/4.png"
    assert color == "#ef4444"  # Fire

def test_fetch_card_image_returns_none_on_empty():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        url, color = fetch_card_image("Unknown Card XYZ", None)
    assert url is None
    assert color == "#64748b"
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest backend/tests/test_pokemontcg.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Create backend/scrapers/pokemontcg.py**

```python
# backend/scrapers/pokemontcg.py
import logging
import requests

logger = logging.getLogger(__name__)

TYPE_COLORS: dict[str, str] = {
    "Fire":       "#ef4444",
    "Water":      "#3b82f6",
    "Grass":      "#22c55e",
    "Psychic":    "#a855f7",
    "Lightning":  "#eab308",
    "Fighting":   "#f97316",
    "Dark":       "#7c3aed",
    "Metal":      "#94a3b8",
    "Dragon":     "#06b6d4",
    "Fairy":      "#ec4899",
    "Colorless":  "#64748b",
}

API_URL = "https://api.pokemontcg.io/v2/cards"


def fetch_card_image(name: str, card_number: str | None) -> tuple[str | None, str]:
    """
    Query pokemontcg.io for the card image URL and derive accent colour from type.
    Returns (image_url, accent_color). image_url may be None; accent_color always has a value.
    """
    try:
        query = f'name:"{name}"'
        if card_number:
            number = card_number.split("/")[0]
            query += f" number:{number}"
        resp = requests.get(
            API_URL,
            params={"q": query, "pageSize": 1},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        card = data.get("data", [None])[0]
        if not card:
            return None, "#64748b"
        image_url = card.get("images", {}).get("small")
        types = card.get("types") or []
        accent = TYPE_COLORS.get(types[0], "#64748b") if types else "#64748b"
        return image_url, accent
    except Exception as e:
        logger.warning(f"pokemontcg lookup failed for {name!r}: {e}")
        return None, "#64748b"
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_pokemontcg.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/scrapers/pokemontcg.py backend/tests/test_pokemontcg.py
git commit -m "feat: pokemontcg.io image + accent colour scraper"
```

---

### Task 5: Expand PriceCharting scraper — all sets, pop, sales, URL

**Files:**
- Modify: `backend/scrapers/pricecharting.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to backend/tests/test_pricecharting.py (create if absent)
from unittest.mock import patch, MagicMock
from backend.scrapers.pricecharting import discover_pokemon_sets, scrape_pricecharting

def test_discover_sets_returns_list_of_strings():
    mock_html = """
    <html><body>
      <a href="/category/pokemon-base-set">Base Set</a>
      <a href="/category/pokemon-scarlet-violet">Scarlet & Violet</a>
      <a href="/category/unrelated">Other</a>
    </body></html>
    """
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = mock_html
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        sets = discover_pokemon_sets()
    assert "pokemon-base-set" in sets
    assert "pokemon-scarlet-violet" in sets
    assert "unrelated" not in sets

def test_scraped_card_has_pricecharting_url():
    from backend.scrapers.pricecharting import ScrapedCard
    card = ScrapedCard(
        name="Charizard", set_name="Base Set", card_number="4",
        pricecharting_id="2412", psa10_price_hkd=42000.0,
        pricecharting_url="https://www.pricecharting.com/game/pokemon-base-set/charizard-4",
        psa_population=3892, sales_per_day=1.2,
    )
    assert card.pricecharting_url.startswith("https://")
    assert card.psa_population == 3892
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest backend/tests/test_pricecharting.py -v
```

Expected: FAIL — `discover_pokemon_sets` not found, `ScrapedCard` missing fields

- [ ] **Step 3: Rewrite backend/scrapers/pricecharting.py**

```python
# backend/scrapers/pricecharting.py
import logging
import re
import requests
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

API_URL = "https://www.pricecharting.com/api/products"
CATEGORY_URL = "https://www.pricecharting.com/category/pokemon-cards"


@dataclass
class ScrapedCard:
    name: str
    set_name: str
    card_number: str
    pricecharting_id: str
    psa10_price_hkd: float
    pricecharting_url: str = ""
    psa_population: int | None = None
    sales_per_day: float | None = None


def discover_pokemon_sets() -> list[str]:
    """Scrape PriceCharting category page to find all Pokemon set slugs."""
    try:
        resp = requests.get(CATEGORY_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        slugs = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Match /category/pokemon-* or /console/pokemon-*
            m = re.match(r"^/(?:category|console)/(pokemon-[^/?#]+)", href)
            if m:
                slug = m.group(1)
                if slug not in slugs:
                    slugs.append(slug)
        logger.info(f"Discovered {len(slugs)} Pokemon sets from PriceCharting")
        return slugs
    except Exception as e:
        logger.error(f"Failed to discover sets: {e}")
        # Fallback: known vintage sets
        return [
            "pokemon-base-set", "pokemon-jungle", "pokemon-fossil",
            "pokemon-team-rocket", "pokemon-neo-genesis", "pokemon-neo-revelation",
            "pokemon-neo-discovery", "pokemon-neo-destiny",
            "pokemon-gym-heroes", "pokemon-gym-challenge",
        ]


def scrape_pricecharting(max_pages: int = 10) -> list[ScrapedCard]:
    """Scrape all PSA 10 cards across all discovered Pokemon sets."""
    set_slugs = discover_pokemon_sets()
    cards = []
    for slug in set_slugs:
        try:
            batch = _scrape_set(slug, max_pages)
            cards.extend(batch)
            logger.info(f"PriceCharting {slug}: {len(batch)} cards")
        except Exception as e:
            logger.error(f"PriceCharting set {slug} failed: {e}")
    logger.info(f"PriceCharting total: {len(cards)} cards")
    return cards


def _scrape_set(set_id: str, max_pages: int) -> list[ScrapedCard]:
    cards = []
    offset = 0
    limit = 100
    for _ in range(max_pages):
        params = {
            "id": set_id, "status": "collection",
            "grade": "10", "slabs": "psa",
            "offset": offset, "limit": limit,
        }
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        products = data if isinstance(data, list) else data.get("products", [])
        if not products:
            break
        for item in products:
            card = _parse_product(item, set_id)
            if card:
                cards.append(card)
        if len(products) < limit:
            break
        offset += limit
    return cards


def _parse_product(item: dict, set_id: str) -> ScrapedCard | None:
    try:
        name = item.get("product-name") or item.get("name") or ""
        set_name = item.get("console-name") or set_id.replace("-", " ").title()
        product_id = str(item.get("id") or "")

        # PriceCharting returns HKD prices when region is HK; fall back to cents→HKD
        price_hkd = item.get("grade-10-hkd") or item.get("psa-10-price-hkd")
        if not price_hkd:
            price_cents = item.get("grade-10") or item.get("psa-10-price") or 0
            if not price_cents:
                return None
            price_hkd = price_cents / 100.0 * 7.8  # rough conversion if no HKD

        if not name or not product_id:
            return None

        name_clean, card_number = _parse_name(name)
        product_slug = item.get("id") or product_id
        pc_url = f"https://www.pricecharting.com/game/{set_id}/{name_clean.lower().replace(' ', '-')}-{card_number}"

        # Sales velocity from API
        sales_per_day = None
        raw_sales = item.get("sales-volume") or item.get("volume")
        if raw_sales is not None:
            try:
                sales_per_day = float(raw_sales)
            except (TypeError, ValueError):
                pass

        return ScrapedCard(
            name=name_clean,
            set_name=set_name,
            card_number=card_number,
            pricecharting_id=product_id,
            psa10_price_hkd=float(price_hkd),
            pricecharting_url=pc_url,
            psa_population=None,  # populated separately by backfill
            sales_per_day=sales_per_day,
        )
    except Exception as e:
        logger.warning(f"PriceCharting product parse failed: {e}")
        return None


def _parse_name(full_name: str) -> tuple[str, str]:
    num_match = re.search(r"#(\S+)", full_name)
    card_number = num_match.group(1) if num_match else ""
    name = re.sub(r"#\S+", "", full_name).strip()
    return name, card_number
```

- [ ] **Step 4: Install beautifulsoup4 if not present**

```bash
pip install beautifulsoup4 && pip freeze | grep beautifulsoup4
```

Add `beautifulsoup4` to `requirements.txt` / `pyproject.toml`.

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_pricecharting.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/scrapers/pricecharting.py backend/tests/test_pricecharting.py
git commit -m "feat: expand PriceCharting scraper to all sets, add pop/sales/URL fields"
```

---

### Task 6: Wire image lookup + pricecharting_url into card creation

**Files:**
- Modify: `backend/scheduler.py`

- [ ] **Step 1: Write failing test**

```python
# Add to backend/tests/test_scheduler.py
from unittest.mock import patch

def test_get_or_create_card_fetches_image_for_new_card(db):
    from backend.scheduler import _get_or_create_card
    with patch("backend.scheduler.fetch_card_image", return_value=("http://img.png", "#ef4444")) as mock_img:
        card = _get_or_create_card(
            db, name="TestImageCard", set_name="Base Set",
            card_number="99", pricecharting_id="img-test-999",
        )
        db.commit()
    assert card.image_url == "http://img.png"
    assert card.accent_color == "#ef4444"
    mock_img.assert_called_once()
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest backend/tests/test_scheduler.py::test_get_or_create_card_fetches_image_for_new_card -v
```

Expected: FAIL

- [ ] **Step 3: Update _get_or_create_card in scheduler.py**

Add import at top of `backend/scheduler.py`:
```python
from backend.scrapers.pokemontcg import fetch_card_image
```

Update the card creation block inside `_get_or_create_card` — replace the `card = Card(...)` block:

```python
    card = Card(
        name=name,
        set_name=set_name,
        card_number=card_number or "",
        pricecharting_id=pricecharting_id,
        snkrdunk_id=snkrdunk_id,
    )
    db.add(card)
    db.flush()
    # Fetch image + accent colour from pokemontcg.io (best-effort)
    try:
        image_url, accent_color = fetch_card_image(name, card_number)
        card.image_url = image_url
        card.accent_color = accent_color
    except Exception as e:
        logger.warning(f"Image fetch failed for {name!r}: {e}")
    return card
```

Also update `_collect_pricecharting` to store `pricecharting_url` on the card:

```python
    for item in scraped:
        try:
            card = _get_or_create_card(
                db, name=item.name, set_name=item.set_name,
                card_number=item.card_number, pricecharting_id=item.pricecharting_id,
            )
            if item.pricecharting_url and not card.pricecharting_url:
                card.pricecharting_url = item.pricecharting_url
            if item.psa_population is not None:
                card.psa_population = item.psa_population
            if item.sales_per_day is not None:
                card.sales_per_day = float(item.sales_per_day)
            price_hkd = round(item.psa10_price_hkd, 2)
            prices[card.id] = price_hkd
        except Exception as e:
            logger.warning(f"PC collect row failed ({item.name}): {e}")
```

Also simplify the snapshot creation in `run_scrape_job` — since prices are now HKD directly:

```python
        for card_id in all_card_ids:
            snap = PriceSnapshot(card_id=card_id)
            if card_id in pc_prices:
                snap.pricecharting_price_hkd = Decimal(str(pc_prices[card_id]))
            if card_id in snkr_prices:
                snap.snkrdunk_price_hkd = Decimal(str(snkr_prices[card_id]))
            db.add(snap)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest backend/tests/test_scheduler.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/scheduler.py
git commit -m "feat: auto-fetch card image + accent colour on creation, store pricecharting_url"
```

---

## Phase 4: Backend API

### Task 7: Update schemas

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Rewrite backend/schemas.py**

```python
# backend/schemas.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date
from typing import Optional


class CardSummary(BaseModel):
    id: UUID
    name: str
    set_name: str
    card_number: Optional[str]
    image_url: Optional[str]
    accent_color: Optional[str]
    snkrdunk_price_hkd: Optional[float]
    pricecharting_price_hkd: Optional[float]
    psa_population: Optional[int]
    trend_7d: Optional[float]
    trend_30d: Optional[float]
    trend_90d: Optional[float]
    trend_1y: Optional[float]
    pct_from_ath: Optional[float]
    trend_consistency: int
    in_watchlist: bool

    model_config = {"from_attributes": True}


class SnapshotPoint(BaseModel):
    scraped_at: datetime
    snkrdunk_price_hkd: Optional[float]
    pricecharting_price_hkd: Optional[float]

    model_config = {"from_attributes": True}


class CardDetail(CardSummary):
    snkrdunk_url: Optional[str]
    pricecharting_url: Optional[str]
    sales_per_day: Optional[float]
    ath: Optional[float]
    ath_date: Optional[datetime]
    history: list[SnapshotPoint]


class WatchlistAdd(BaseModel):
    card_id: UUID


class PortfolioItemOut(BaseModel):
    id: UUID
    card_id: UUID
    name: str
    set_name: str
    card_number: Optional[str]
    image_url: Optional[str]
    accent_color: Optional[str]
    psa_population: Optional[int]
    purchase_price_hkd: float
    purchased_at: date
    current_price_hkd: Optional[float]
    pnl_hkd: Optional[float]
    pnl_pct: Optional[float]
    trend_30d: Optional[float]

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    items: list[PortfolioItemOut]
    total_invested: float
    total_current_value: float
    total_pnl_hkd: float
    total_pnl_pct: Optional[float]


class PortfolioAdd(BaseModel):
    card_id: UUID
    purchase_price_hkd: float
    purchased_at: date
```

- [ ] **Step 2: Run existing tests to check nothing explodes**

```bash
python -m pytest backend/tests/test_cards_router.py backend/tests/test_watchlist_router.py -v
```

Fix any import errors caused by schema changes before proceeding.

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: update schemas with new card fields, portfolio types"
```

---

### Task 8: Update cards router with new computed metrics

**Files:**
- Modify: `backend/routers/cards.py`
- Modify: `backend/tests/test_cards_router.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to backend/tests/test_cards_router.py
def test_get_cards_returns_new_fields(client, db):
    _seed_card(db)
    resp = client.get("/cards")
    assert resp.status_code == 200
    data = resp.json()
    # May be empty if no positive trend — seed with two snaps so trend can be computed
    # (existing _seed_card only adds one snap, so cards list may be empty — that's correct)
    assert isinstance(data, list)

def test_get_card_detail_has_new_fields(client, db):
    card = _seed_card(db, name="DetailTest")
    resp = client.get(f"/cards/{card.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "pct_from_ath" in data
    assert "trend_consistency" in data
    assert "ath" in data
    assert "ath_date" in data
    assert "trend_1y" in data
    assert "history" in data
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest backend/tests/test_cards_router.py -v -k "new_fields"
```

Expected: FAIL — fields missing

- [ ] **Step 3: Rewrite backend/routers/cards.py**

```python
# backend/routers/cards.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models import Card, PriceSnapshot, WatchlistItem
from backend.schemas import CardSummary, CardDetail, SnapshotPoint
from backend.scoring import (
    calculate_trend_vs_days_ago, calculate_ath,
    calculate_pct_from_ath, calculate_trend_consistency,
)

router = APIRouter(prefix="/cards", tags=["cards"])


def _snap_in_window(snap, cutoff) -> bool:
    from datetime import timezone
    dt = snap.scraped_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


def _latest_price(snaps, field: str):
    for snap in sorted(snaps, key=lambda s: s.scraped_at, reverse=True):
        val = getattr(snap, field)
        if val:
            return float(val)
    return None


def _card_metrics(snapshots: list) -> dict:
    ath, ath_date = calculate_ath(snapshots)
    return {
        "trend_7d":          calculate_trend_vs_days_ago(snapshots, 7),
        "trend_30d":         calculate_trend_vs_days_ago(snapshots, 30),
        "trend_90d":         calculate_trend_vs_days_ago(snapshots, 90),
        "trend_1y":          calculate_trend_vs_days_ago(snapshots, 365),
        "pct_from_ath":      calculate_pct_from_ath(snapshots),
        "trend_consistency": calculate_trend_consistency(snapshots),
        "ath":               ath,
        "ath_date":          ath_date,
    }


def _build_summary(card: Card, metrics: dict, watchlist_ids: set) -> CardSummary:
    snaps = card.snapshots
    return CardSummary(
        id=card.id,
        name=card.name,
        set_name=card.set_name,
        card_number=card.card_number,
        image_url=card.image_url,
        accent_color=card.accent_color,
        snkrdunk_price_hkd=_latest_price(snaps, "snkrdunk_price_hkd"),
        pricecharting_price_hkd=_latest_price(snaps, "pricecharting_price_hkd"),
        psa_population=card.psa_population,
        trend_7d=metrics["trend_7d"],
        trend_30d=metrics["trend_30d"],
        trend_90d=metrics["trend_90d"],
        trend_1y=metrics["trend_1y"],
        pct_from_ath=metrics["pct_from_ath"],
        trend_consistency=metrics["trend_consistency"],
        in_watchlist=card.id in watchlist_ids,
    )


@router.get("", response_model=list[CardSummary])
def get_cards(
    sort: str = Query("trend_30d"),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db),
):
    valid_sorts = {"trend_7d", "trend_30d", "trend_90d", "trend_1y"}
    if sort not in valid_sorts:
        sort = "trend_30d"

    query = db.query(Card)
    if search:
        query = query.filter(Card.name.ilike(f"%{search}%"))
    cards = query.all()

    watchlist_ids = {w.card_id for w in db.query(WatchlistItem).all()}

    results = []
    for card in cards:
        metrics = _card_metrics(card.snapshots)
        trend = metrics[sort]
        if trend is None or trend <= 0:
            continue  # only show upward-trending cards on home page
        results.append((card, metrics))

    results.sort(key=lambda x: x[1][sort] or float("-inf"), reverse=True)
    results = results[:limit]

    return [_build_summary(card, metrics, watchlist_ids) for card, metrics in results]


@router.get("/{card_id}", response_model=CardDetail)
def get_card(card_id: str, db: Session = Depends(get_db)):
    import uuid as _uuid
    try:
        card_uuid = _uuid.UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Card not found")
    card = db.query(Card).filter(Card.id == card_uuid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    watchlist_ids = {w.card_id for w in db.query(WatchlistItem).all()}
    metrics = _card_metrics(card.snapshots)

    history = [
        SnapshotPoint(
            scraped_at=snap.scraped_at,
            snkrdunk_price_hkd=float(snap.snkrdunk_price_hkd) if snap.snkrdunk_price_hkd else None,
            pricecharting_price_hkd=float(snap.pricecharting_price_hkd) if snap.pricecharting_price_hkd else None,
        )
        for snap in sorted(card.snapshots, key=lambda x: x.scraped_at)
    ]

    return CardDetail(
        **_build_summary(card, metrics, watchlist_ids).model_dump(),
        snkrdunk_url=card.snkrdunk_url,
        pricecharting_url=card.pricecharting_url,
        sales_per_day=float(card.sales_per_day) if card.sales_per_day else None,
        ath=metrics["ath"],
        ath_date=metrics["ath_date"],
        history=history,
    )
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest backend/tests/ -v
```

Fix any failures before proceeding.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/cards.py backend/tests/test_cards_router.py
git commit -m "feat: cards router — new metrics, upward-trend filter, sort param"
```

---

### Task 9: Portfolio router

**Files:**
- Create: `backend/routers/portfolio.py`
- Create: `backend/tests/test_portfolio_router.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_portfolio_router.py
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from backend.models import Card, PriceSnapshot, PortfolioItem


def _seed_card_with_price(db, name="Pikachu"):
    card = Card(id=uuid.uuid4(), name=name, set_name="Base Set", card_number="58")
    snap = PriceSnapshot(
        id=uuid.uuid4(), card_id=card.id,
        pricecharting_price_hkd=Decimal("10000"),
        scraped_at=datetime.now(timezone.utc),
    )
    db.add(card); db.add(snap); db.commit()
    return card


def test_add_and_get_portfolio_item(client, db):
    card = _seed_card_with_price(db)
    resp = client.post("/portfolio", json={
        "card_id": str(card.id),
        "purchase_price_hkd": 8000.0,
        "purchased_at": "2025-01-15",
    })
    assert resp.status_code == 200

    resp = client.get("/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["name"] == "Pikachu"
    assert data["items"][0]["pnl_hkd"] == 2000.0
    assert data["total_invested"] == 8000.0


def test_delete_portfolio_item(client, db):
    card = _seed_card_with_price(db, name="Raichu")
    add_resp = client.post("/portfolio", json={
        "card_id": str(card.id),
        "purchase_price_hkd": 5000.0,
        "purchased_at": "2025-03-01",
    })
    item_id = client.get("/portfolio").json()["items"][0]["id"]
    del_resp = client.delete(f"/portfolio/{item_id}")
    assert del_resp.status_code == 200
    assert client.get("/portfolio").json()["items"] == []
```

- [ ] **Step 2: Run to verify fail**

```bash
python -m pytest backend/tests/test_portfolio_router.py -v
```

Expected: FAIL — 404 on /portfolio

- [ ] **Step 3: Create backend/routers/portfolio.py**

```python
# backend/routers/portfolio.py
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Card, PortfolioItem
from backend.schemas import PortfolioAdd, PortfolioItemOut, PortfolioSummary
from backend.routers.cards import _latest_price, _card_metrics

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioSummary)
def get_portfolio(db: Session = Depends(get_db)):
    items = db.query(PortfolioItem).all()
    out = []
    total_invested = 0.0
    total_current = 0.0

    for item in items:
        card = item.card
        current = _latest_price(card.snapshots, "pricecharting_price_hkd") or \
                  _latest_price(card.snapshots, "snkrdunk_price_hkd")
        paid = float(item.purchase_price_hkd)
        pnl_hkd = (current - paid) if current else None
        pnl_pct = ((current - paid) / paid * 100) if current and paid else None
        metrics = _card_metrics(card.snapshots)
        total_invested += paid
        if current:
            total_current += current
        out.append(PortfolioItemOut(
            id=item.id,
            card_id=item.card_id,
            name=card.name,
            set_name=card.set_name,
            card_number=card.card_number,
            image_url=card.image_url,
            accent_color=card.accent_color,
            psa_population=card.psa_population,
            purchase_price_hkd=paid,
            purchased_at=item.purchased_at,
            current_price_hkd=current,
            pnl_hkd=round(pnl_hkd, 2) if pnl_hkd is not None else None,
            pnl_pct=round(pnl_pct, 2) if pnl_pct is not None else None,
            trend_30d=metrics["trend_30d"],
        ))

    pnl_total = total_current - total_invested
    pnl_pct_total = (pnl_total / total_invested * 100) if total_invested else None
    return PortfolioSummary(
        items=sorted(out, key=lambda x: x.pnl_pct or float("-inf"), reverse=True),
        total_invested=round(total_invested, 2),
        total_current_value=round(total_current, 2),
        total_pnl_hkd=round(pnl_total, 2),
        total_pnl_pct=round(pnl_pct_total, 2) if pnl_pct_total is not None else None,
    )


@router.post("", response_model=dict)
def add_portfolio_item(body: PortfolioAdd, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == body.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    item = PortfolioItem(
        id=uuid.uuid4(),
        card_id=body.card_id,
        purchase_price_hkd=Decimal(str(body.purchase_price_hkd)),
        purchased_at=body.purchased_at,
    )
    db.add(item)
    db.commit()
    return {"ok": True, "id": str(item.id)}


@router.delete("/{item_id}", response_model=dict)
def delete_portfolio_item(item_id: str, db: Session = Depends(get_db)):
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")
    item = db.query(PortfolioItem).filter(PortfolioItem.id == item_uuid).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Register the router in main.py**

Add to `backend/main.py`:
```python
from backend.routers import cards, watchlist, report, portfolio
# ...
app.include_router(portfolio.router)
```

- [ ] **Step 5: Add PortfolioItem to conftest client**

In `backend/tests/conftest.py`, ensure `PortfolioItem` is covered by the test schema (it should be automatic if `Base.metadata.create_all` is used).

- [ ] **Step 6: Run all tests**

```bash
python -m pytest backend/tests/ -v
```

Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add backend/routers/portfolio.py backend/tests/test_portfolio_router.py backend/main.py
git commit -m "feat: portfolio router — GET/POST/DELETE /portfolio with P&L"
```

---

## Phase 5: Frontend

### Task 10: Global layout — per-route background + updated nav

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Update types.ts**

```typescript
// frontend/src/lib/types.ts
export interface CardSummary {
  id: string;
  name: string;
  set_name: string;
  card_number: string | null;
  image_url: string | null;
  accent_color: string | null;
  snkrdunk_price_hkd: number | null;
  pricecharting_price_hkd: number | null;
  psa_population: number | null;
  trend_7d: number | null;
  trend_30d: number | null;
  trend_90d: number | null;
  trend_1y: number | null;
  pct_from_ath: number | null;
  trend_consistency: number;
  in_watchlist: boolean;
}

export interface SnapshotPoint {
  scraped_at: string;
  snkrdunk_price_hkd: number | null;
  pricecharting_price_hkd: number | null;
}

export interface CardDetail extends CardSummary {
  snkrdunk_url: string | null;
  pricecharting_url: string | null;
  sales_per_day: number | null;
  ath: number | null;
  ath_date: string | null;
  history: SnapshotPoint[];
}

export interface PortfolioItem {
  id: string;
  card_id: string;
  name: string;
  set_name: string;
  card_number: string | null;
  image_url: string | null;
  accent_color: string | null;
  psa_population: number | null;
  purchase_price_hkd: number;
  purchased_at: string;
  current_price_hkd: number | null;
  pnl_hkd: number | null;
  pnl_pct: number | null;
  trend_30d: number | null;
}

export interface PortfolioSummary {
  items: PortfolioItem[];
  total_invested: number;
  total_current_value: number;
  total_pnl_hkd: number;
  total_pnl_pct: number | null;
}
```

- [ ] **Step 2: Update api.ts**

```typescript
// frontend/src/lib/api.ts
import type { CardSummary, CardDetail, PortfolioSummary } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

export interface CardFilters {
  search?: string;
  sort?: "trend_7d" | "trend_30d" | "trend_90d" | "trend_1y";
  limit?: number;
}

export function cardsUrl(f: CardFilters = {}): string {
  const p = new URLSearchParams();
  if (f.search) p.set("search", f.search);
  if (f.sort) p.set("sort", f.sort);
  if (f.limit) p.set("limit", String(f.limit));
  return `${BASE}/cards?${p}`;
}

export const fetchCards = (url: string): Promise<CardSummary[]> => fetcher(url);
export const fetchCard = (id: string): Promise<CardDetail> =>
  fetcher(`${BASE}/cards/${id}`);
export const fetchPortfolio = (): Promise<PortfolioSummary> =>
  fetcher(`${BASE}/portfolio`);

export async function addPortfolioItem(body: {
  card_id: string;
  purchase_price_hkd: number;
  purchased_at: string;
}): Promise<{ ok: boolean; id: string }> {
  const r = await fetch(`${BASE}/portfolio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function deletePortfolioItem(id: string): Promise<void> {
  await fetch(`${BASE}/portfolio/${id}`, { method: "DELETE" });
}

export async function toggleWatchlist(
  cardId: string, inWatchlist: boolean
): Promise<void> {
  if (inWatchlist) {
    await fetch(`${BASE}/watchlist/${cardId}`, { method: "DELETE" });
  } else {
    await fetch(`${BASE}/watchlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ card_id: cardId }),
    });
  }
}
```

- [ ] **Step 3: Update layout.tsx**

```tsx
// frontend/src/app/layout.tsx
"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";

const BG_MAP: Record<string, string> = {
  "/":           "/backgrounds/home.jpg",
  "/card":       "/backgrounds/detail.jpg",
  "/my-cards":   "/backgrounds/my-cards.jpg",
  "/watchlist":  "/backgrounds/watchlist.jpg",
};

function getBackground(pathname: string): string {
  if (pathname.startsWith("/card/")) return BG_MAP["/card"];
  return BG_MAP[pathname] ?? BG_MAP["/"];
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const bg = getBackground(pathname);

  return (
    <html lang="en">
      <body className="min-h-screen text-gray-100" style={{ backgroundColor: "#080c14" }}>
        {/* Full-bleed background */}
        <div
          className="fixed inset-0 -z-10 bg-cover bg-center"
          style={{
            backgroundImage: `url(${bg})`,
            filter: "brightness(0.18)",
          }}
        />

        {/* Nav */}
        <nav className="sticky top-0 z-50 border-b border-white/5"
             style={{ background: "rgba(8, 12, 20, 0.85)", backdropFilter: "blur(8px)" }}>
          <div className="max-w-7xl mx-auto px-4 h-12 flex items-center gap-6">
            <span className="font-bold text-sm text-gray-100 tracking-wide">
              PokéInvest
            </span>
            <div className="flex gap-4 ml-4">
              {[
                { href: "/", label: "Home" },
                { href: "/my-cards", label: "My Cards" },
                { href: "/watchlist", label: "Watchlist" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`text-sm transition-colors ${
                    pathname === href
                      ? "text-white font-semibold"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </nav>

        {/* Page content */}
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: per-route Pokemon background, updated nav, new API/type definitions"
```

---

### Task 11: Home page — new CardTable

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/CardTable.tsx`

- [ ] **Step 1: Update page.tsx**

```tsx
// frontend/src/app/page.tsx
"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import { cardsUrl, fetchCards, type CardFilters } from "@/lib/api";
import CardTable from "@/components/CardTable";

export default function HomePage() {
  const [filters, setFilters] = useState<CardFilters>({ sort: "trend_30d" });
  const url = cardsUrl(filters);
  const { data, error, isLoading } = useSWR(url, fetchCards, { refreshInterval: 60_000 });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Top Trending PSA 10 Cards</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.length} cards` : "Loading…"} · sorted by {filters.sort ?? "30d"} trend
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Search cards…"
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-gray-100 w-48 focus:outline-none focus:border-white/30 backdrop-blur"
          />
          <select
            value={filters.sort ?? "trend_30d"}
            onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value as CardFilters["sort"] }))}
            className="bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none backdrop-blur"
          >
            <option value="trend_7d">Sort: 7d</option>
            <option value="trend_30d">Sort: 30d</option>
            <option value="trend_90d">Sort: 90d</option>
            <option value="trend_1y">Sort: 1y</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-950/60 border border-red-800/60 px-4 py-3 text-sm text-red-300 backdrop-blur">
          Failed to load cards — is the backend running?
        </div>
      )}
      {isLoading && (
        <div className="text-center py-16 text-gray-500 animate-pulse">Loading cards…</div>
      )}
      {data && <CardTable cards={data} activeSort={filters.sort ?? "trend_30d"} />}
    </div>
  );
}
```

- [ ] **Step 2: Rewrite CardTable.tsx**

```tsx
// frontend/src/components/CardTable.tsx
"use client";

import { useRouter } from "next/navigation";
import type { CardSummary } from "@/lib/types";
import WatchlistButton from "./WatchlistButton";

interface Props {
  cards: CardSummary[];
  activeSort: string;
}

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

function TrendCell({ value, bold }: { value: number | null; bold?: boolean }) {
  if (value == null) return <span className="text-gray-600">—</span>;
  const up = value > 0;
  const cls = `tabular-nums ${bold ? "font-bold text-base" : "font-medium text-sm"} ${
    up ? "text-green-400" : "text-red-400"
  }`;
  return <span className={cls}>{up ? "▲" : "▼"}{Math.abs(value).toFixed(1)}%</span>;
}

function AthCell({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-600">—</span>;
  const color = value >= -10 ? "text-amber-400" : "text-red-400";
  return <span className={`tabular-nums text-sm font-medium ${color}`}>{value.toFixed(1)}%</span>;
}

export default function CardTable({ cards, activeSort }: Props) {
  const router = useRouter();

  if (cards.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        No cards with an upward trend found. Run a scrape or backfill to populate data.
      </div>
    );
  }

  const cols = [
    { key: "trend_7d", label: "7d" },
    { key: "trend_30d", label: "30d" },
    { key: "trend_90d", label: "90d" },
    { key: "trend_1y", label: "1y" },
  ];

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10"
         style={{ background: "rgba(15, 23, 42, 0.7)", backdropFilter: "blur(6px)" }}>
      <table className="w-full text-sm min-w-[800px]">
        <thead>
          <tr className="border-b border-white/10">
            <th className="px-3 py-2 w-8" />
            <th className="px-3 py-2 w-[72px]" />
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Card</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide whitespace-nowrap">Price (HKD)</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">vs ATH</th>
            {cols.map(({ key, label }) => (
              <th key={key}
                  className={`px-3 py-2 text-right text-xs font-medium uppercase tracking-wide whitespace-nowrap ${
                    activeSort === key ? "text-blue-400" : "text-gray-400"
                  }`}>
                {label}{activeSort === key ? " ↓" : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {cards.map((card) => (
            <tr
              key={card.id}
              onClick={() => router.push(`/card/${card.id}`)}
              className="hover:bg-white/5 cursor-pointer transition-colors"
              style={{ borderLeft: `3px solid ${card.accent_color ?? "#64748b"}` }}
            >
              <td className="px-3 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                <WatchlistButton cardId={card.id} inWatchlist={card.in_watchlist} />
              </td>
              <td className="px-3 py-2">
                {card.image_url ? (
                  <img src={card.image_url} alt={card.name}
                       className="w-[54px] h-[76px] object-contain rounded" />
                ) : (
                  <div className="w-[54px] h-[76px] rounded bg-white/5" />
                )}
              </td>
              <td className="px-3 py-2">
                <div className="font-semibold text-gray-100">{card.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {card.card_number && `${card.card_number} · `}{card.set_name}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {card.psa_population != null && (
                    <span className="text-[10px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-gray-400">
                      Pop: {card.psa_population.toLocaleString()}
                    </span>
                  )}
                  {card.trend_consistency > 0 && (
                    <span className="text-[10px] text-green-400">
                      {card.trend_consistency}/4 wks ↑
                    </span>
                  )}
                </div>
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-200 whitespace-nowrap">
                {hkd(card.pricecharting_price_hkd ?? card.snkrdunk_price_hkd)}
                <div className="text-[10px] text-gray-600">
                  {card.pricecharting_price_hkd ? "PriceCharting" : card.snkrdunk_price_hkd ? "Snkrdunk" : ""}
                </div>
              </td>
              <td className="px-3 py-2 text-right"><AthCell value={card.pct_from_ath} /></td>
              {cols.map(({ key }) => (
                <td key={key} className="px-3 py-2 text-right">
                  <TrendCell
                    value={card[key as keyof CardSummary] as number | null}
                    bold={activeSort === key}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/components/CardTable.tsx
git commit -m "feat: home page — new table with pop, ATH, consistency, all trend columns"
```

---

### Task 12: Card Detail page rebuild

**Files:**
- Modify: `frontend/src/app/card/[id]/page.tsx`
- Create: `frontend/src/components/PopChart.tsx`

- [ ] **Step 1: Create PopChart.tsx**

```tsx
// frontend/src/components/PopChart.tsx
"use client";

interface Props {
  population: number;
}

export default function PopChart({ population }: Props) {
  return (
    <div className="rounded-lg border border-white/10 p-4"
         style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
      <div className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-3">
        PSA 10 Population
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-gray-100 tabular-nums">
          {population.toLocaleString()}
        </span>
        <span className="text-sm text-gray-500">copies graded PSA 10</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Rewrite card/[id]/page.tsx**

```tsx
// frontend/src/app/card/[id]/page.tsx
"use client";

import { use, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { fetchCard } from "@/lib/api";
import WatchlistButton from "@/components/WatchlistButton";
import PriceChart from "@/components/PriceChart";
import PopChart from "@/components/PopChart";

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

function TrendTile({ label, value, active }: { label: string; value: number | null; active?: boolean }) {
  const up = value != null && value > 0;
  const down = value != null && value < 0;
  return (
    <div className={`rounded-lg border p-3 text-center ${active ? "border-blue-500/50" : "border-white/10"}`}
         style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
      <div className={`text-xs uppercase tracking-wide mb-1 ${active ? "text-blue-400" : "text-gray-500"}`}>{label}</div>
      <div className={`text-xl font-bold tabular-nums ${
        value == null ? "text-gray-600" : up ? "text-green-400" : down ? "text-red-400" : "text-gray-300"
      }`}>
        {value == null ? "—" : `${up ? "▲" : "▼"}${Math.abs(value).toFixed(1)}%`}
      </div>
    </div>
  );
}

export default function CardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: card, error, isLoading } = useSWR(id, fetchCard);
  const [range, setRange] = useState<"6m" | "1y" | "all">("1y");

  if (isLoading) return <div className="text-center py-16 text-gray-500 animate-pulse">Loading…</div>;
  if (error || !card) return (
    <div className="text-center py-16 text-red-400">
      Card not found. <Link href="/" className="text-blue-400 hover:underline">Back to cards</Link>
    </div>
  );

  const currentPrice = card.pricecharting_price_hkd ?? card.snkrdunk_price_hkd;

  // Filter history by selected range
  const now = Date.now();
  const rangeDays = range === "6m" ? 180 : range === "1y" ? 365 : Infinity;
  const filteredHistory = card.history.filter((h) => {
    const diff = (now - new Date(h.scraped_at).getTime()) / 86400000;
    return diff <= rangeDays;
  });

  return (
    <div className="space-y-5 max-w-4xl">
      <Link href="/" className="text-sm text-gray-500 hover:text-gray-300">← Back to Top 50</Link>

      {/* Header */}
      <div className="flex gap-6 items-start">
        {/* Card image */}
        <div className="flex-shrink-0">
          {card.image_url ? (
            <img src={card.image_url} alt={card.name} className="w-40 rounded-lg shadow-xl" />
          ) : (
            <div className="w-40 h-56 rounded-lg bg-white/5 border border-white/10" />
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-gray-100 leading-tight">{card.name}</h1>
          <p className="text-gray-400 mt-1">
            {card.card_number && <span className="mr-2">#{card.card_number}</span>}
            {card.set_name}
          </p>

          <div className="flex flex-wrap gap-2 mt-3">
            <span className="bg-green-950/50 border border-green-700/50 text-green-400 text-xs rounded px-2 py-0.5">PSA 10</span>
            {card.psa_population != null && (
              <span className="bg-white/5 border border-white/10 text-gray-400 text-xs rounded px-2 py-0.5">
                Pop: {card.psa_population.toLocaleString()}
              </span>
            )}
            {card.sales_per_day != null && (
              <span className="bg-white/5 border border-white/10 text-gray-400 text-xs rounded px-2 py-0.5">
                {card.sales_per_day.toFixed(1)} sales/day
              </span>
            )}
          </div>

          <div className="mt-3 space-y-1 text-sm">
            {card.trend_consistency > 0 && (
              <div className="text-green-400">{card.trend_consistency}/4 weeks ↑ (trend consistency)</div>
            )}
            {card.pct_from_ath != null && (
              <div className={card.pct_from_ath >= -10 ? "text-amber-400" : "text-red-400"}>
                {card.pct_from_ath.toFixed(1)}% from ATH
                {card.ath != null && (
                  <span className="text-gray-500 ml-1">
                    (ATH: {hkd(card.ath)}{card.ath_date ? ` · ${new Date(card.ath_date).toLocaleDateString("en-HK", { year: "numeric", month: "short" })}` : ""})
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="mt-4">
            <WatchlistButton cardId={card.id} inWatchlist={card.in_watchlist} />
          </div>
        </div>
      </div>

      {/* Price panels */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: "Snkrdunk · PSA 10", value: card.snkrdunk_price_hkd, url: card.snkrdunk_url, linkLabel: "View on Snkrdunk ↗" },
          { label: "PriceCharting · PSA 10", value: card.pricecharting_price_hkd, url: card.pricecharting_url, linkLabel: "View on PriceCharting ↗" },
        ].map(({ label, value, url, linkLabel }) => (
          <div key={label} className="rounded-lg border border-white/10 p-4"
               style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
            <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
            <div className="text-2xl font-bold text-gray-100 tabular-nums mt-1">{hkd(value)}</div>
            {url ? (
              <a href={url} target="_blank" rel="noopener noreferrer"
                 className="text-xs text-blue-400 hover:underline mt-2 inline-block"
                 onClick={(e) => e.stopPropagation()}>
                {linkLabel}
              </a>
            ) : (
              <div className="text-xs text-gray-600 mt-2">No link available</div>
            )}
          </div>
        ))}
      </div>

      {/* Trend tiles */}
      <div className="grid grid-cols-4 gap-3">
        <TrendTile label="7 days" value={card.trend_7d} />
        <TrendTile label="30 days" value={card.trend_30d} active />
        <TrendTile label="90 days" value={card.trend_90d} />
        <TrendTile label="1 year" value={card.trend_1y} />
      </div>

      {/* Price history chart */}
      <div className="rounded-lg border border-white/10 p-4"
           style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs text-gray-400 uppercase tracking-wide font-medium">PSA 10 Price History</div>
          <div className="flex gap-1">
            {(["6m", "1y", "all"] as const).map((r) => (
              <button key={r} onClick={() => setRange(r)}
                      className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                        range === r ? "border-blue-500 text-blue-400" : "border-white/10 text-gray-500 hover:border-white/30"
                      }`}>
                {r}
              </button>
            ))}
          </div>
        </div>
        <PriceChart history={filteredHistory} />
      </div>

      {/* PSA pop */}
      {card.psa_population != null && <PopChart population={card.psa_population} />}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/card/[id]/page.tsx frontend/src/components/PopChart.tsx
git commit -m "feat: card detail page rebuild — pop, ATH, trend tiles, source links, chart range"
```

---

### Task 13: My Cards page

**Files:**
- Create: `frontend/src/app/my-cards/page.tsx`
- Create: `frontend/src/components/PortfolioTable.tsx`
- Create: `frontend/src/components/AddCardModal.tsx`

- [ ] **Step 1: Create AddCardModal.tsx**

```tsx
// frontend/src/components/AddCardModal.tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { cardsUrl, fetchCards, addPortfolioItem } from "@/lib/api";

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

export default function AddCardModal({ onClose, onAdded }: Props) {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState("");
  const [price, setPrice] = useState("");
  const [purchasedAt, setPurchasedAt] = useState(new Date().toISOString().split("T")[0]);
  const [saving, setSaving] = useState(false);

  const { data: results } = useSWR(
    search.length >= 2 ? cardsUrl({ search, limit: 10 }) : null,
    fetchCards
  );

  async function handleAdd() {
    if (!selectedId || !price || !purchasedAt) return;
    setSaving(true);
    await addPortfolioItem({
      card_id: selectedId,
      purchase_price_hkd: parseFloat(price),
      purchased_at: purchasedAt,
    });
    setSaving(false);
    onAdded();
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         style={{ background: "rgba(0,0,0,0.7)" }} onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border border-white/10 p-6 space-y-4"
           style={{ background: "rgba(15, 23, 42, 0.95)", backdropFilter: "blur(12px)" }}
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-gray-100">Add Card to Portfolio</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400">Search card</label>
          <input
            type="text" value={search} placeholder="Type card name…"
            onChange={(e) => { setSearch(e.target.value); setSelectedId(null); setSelectedName(""); }}
            className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-white/30"
          />
          {results && results.length > 0 && !selectedId && (
            <div className="border border-white/10 rounded-lg overflow-hidden max-h-48 overflow-y-auto">
              {results.map((c) => (
                <button key={c.id}
                        onClick={() => { setSelectedId(c.id); setSelectedName(c.name); setSearch(c.name); }}
                        className="w-full text-left px-3 py-2 text-sm text-gray-200 hover:bg-white/5 border-b border-white/5 last:border-0">
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-gray-500">{c.set_name}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-gray-400">Purchase price (HKD)</label>
            <input type="number" value={price} onChange={(e) => setPrice(e.target.value)}
                   placeholder="e.g. 18000"
                   className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-white/30" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-400">Purchase date</label>
            <input type="date" value={purchasedAt} onChange={(e) => setPurchasedAt(e.target.value)}
                   className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-white/30" />
          </div>
        </div>

        <button
          onClick={handleAdd}
          disabled={!selectedId || !price || saving}
          className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg py-2 text-sm font-medium transition-colors"
        >
          {saving ? "Adding…" : "Add to My Cards"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create PortfolioTable.tsx**

```tsx
// frontend/src/components/PortfolioTable.tsx
"use client";

import { useRouter } from "next/navigation";
import type { PortfolioItem } from "@/lib/types";
import { deletePortfolioItem } from "@/lib/api";

interface Props {
  items: PortfolioItem[];
  onDelete: () => void;
}

const hkd = (v: number | null) =>
  v == null ? "—" : `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

export default function PortfolioTable({ items, onDelete }: Props) {
  const router = useRouter();

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    await deletePortfolioItem(id);
    onDelete();
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-white/10"
         style={{ background: "rgba(15, 23, 42, 0.7)", backdropFilter: "blur(6px)" }}>
      <table className="w-full text-sm min-w-[700px]">
        <thead>
          <tr className="border-b border-white/10">
            <th className="px-3 py-2 w-[72px]" />
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wide">Card</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Bought</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Paid</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">Now</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">P&amp;L</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-400 uppercase tracking-wide">30d</th>
            <th className="px-3 py-2 w-8" />
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {items.map((item) => (
            <tr key={item.id}
                onClick={() => router.push(`/card/${item.card_id}`)}
                className="hover:bg-white/5 cursor-pointer transition-colors"
                style={{ borderLeft: `3px solid ${item.accent_color ?? "#64748b"}` }}>
              <td className="px-3 py-2">
                {item.image_url ? (
                  <img src={item.image_url} alt={item.name} className="w-[54px] h-[76px] object-contain rounded" />
                ) : (
                  <div className="w-[54px] h-[76px] rounded bg-white/5" />
                )}
              </td>
              <td className="px-3 py-2">
                <div className="font-semibold text-gray-100">{item.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {item.card_number && `${item.card_number} · `}{item.set_name}
                </div>
                {item.psa_population != null && (
                  <span className="text-[10px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-gray-400 mt-1 inline-block">
                    Pop: {item.psa_population.toLocaleString()}
                  </span>
                )}
              </td>
              <td className="px-3 py-2 text-right text-gray-500 text-xs whitespace-nowrap">{item.purchased_at}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-400 whitespace-nowrap">{hkd(item.purchase_price_hkd)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-100 font-semibold whitespace-nowrap">{hkd(item.current_price_hkd)}</td>
              <td className="px-3 py-2 text-right whitespace-nowrap">
                {item.pnl_hkd != null ? (
                  <>
                    <div className={`font-bold tabular-nums ${item.pnl_hkd >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {item.pnl_hkd >= 0 ? "+" : ""}{hkd(item.pnl_hkd)}
                    </div>
                    <div className={`text-xs tabular-nums ${item.pnl_pct != null && item.pnl_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {item.pnl_pct != null ? `${item.pnl_pct >= 0 ? "+" : ""}${item.pnl_pct.toFixed(1)}%` : ""}
                    </div>
                  </>
                ) : <span className="text-gray-600">—</span>}
              </td>
              <td className="px-3 py-2 text-right">
                {item.trend_30d != null ? (
                  <span className={`text-sm tabular-nums font-medium ${item.trend_30d >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {item.trend_30d >= 0 ? "▲" : "▼"}{Math.abs(item.trend_30d).toFixed(1)}%
                  </span>
                ) : <span className="text-gray-600">—</span>}
              </td>
              <td className="px-3 py-2 text-center" onClick={(e) => handleDelete(e, item.id)}>
                <span className="text-gray-600 hover:text-red-400 transition-colors cursor-pointer">✕</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Create my-cards/page.tsx**

```tsx
// frontend/src/app/my-cards/page.tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetchPortfolio } from "@/lib/api";
import PortfolioTable from "@/components/PortfolioTable";
import AddCardModal from "@/components/AddCardModal";

const hkd = (v: number) => `HK$${v.toLocaleString("en-HK", { maximumFractionDigits: 0 })}`;

export default function MyCardsPage() {
  const { data, error, isLoading, mutate } = useSWR("portfolio", fetchPortfolio);
  const [showModal, setShowModal] = useState(false);

  return (
    <div className="space-y-5">
      {/* Summary bar */}
      {data && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Cards Owned", value: String(data.items.length) },
            { label: "Total Invested", value: hkd(data.total_invested) },
            { label: "Current Value", value: hkd(data.total_current_value) },
            {
              label: "Total P&L",
              value: `${data.total_pnl_hkd >= 0 ? "+" : ""}${hkd(data.total_pnl_hkd)}`,
              sub: data.total_pnl_pct != null
                ? `${data.total_pnl_pct >= 0 ? "+" : ""}${data.total_pnl_pct.toFixed(1)}%`
                : undefined,
              color: data.total_pnl_hkd >= 0 ? "text-green-400" : "text-red-400",
            },
          ].map(({ label, value, sub, color }) => (
            <div key={label} className="rounded-lg border border-white/10 px-4 py-3"
                 style={{ background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)" }}>
              <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
              <div className={`text-xl font-bold tabular-nums mt-1 ${color ?? "text-gray-100"}`}>{value}</div>
              {sub && <div className={`text-xs tabular-nums ${color}`}>{sub}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">My Cards</h1>
          <p className="text-sm text-gray-500 mt-0.5">Sorted by P&L % · best performers first</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg px-4 py-2 transition-colors"
        >
          + Add Card
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-950/60 border border-red-800/60 px-4 py-3 text-sm text-red-300 backdrop-blur">
          Failed to load portfolio — is the backend running?
        </div>
      )}
      {isLoading && <div className="text-center py-16 text-gray-500 animate-pulse">Loading…</div>}
      {data && data.items.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          No cards yet. Click &ldquo;+ Add Card&rdquo; to track your first purchase.
        </div>
      )}
      {data && data.items.length > 0 && (
        <PortfolioTable items={data.items} onDelete={() => mutate()} />
      )}

      {showModal && (
        <AddCardModal onClose={() => setShowModal(false)} onAdded={() => mutate()} />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/my-cards/page.tsx frontend/src/components/PortfolioTable.tsx frontend/src/components/AddCardModal.tsx
git commit -m "feat: My Cards page — portfolio tracker with P&L, add/remove cards"
```

---

## Phase 6: Deploy

### Task 14: Push to production and trigger data population

**Files:**
- Modify: `frontend/src/components/ScrapeTrigger.tsx` (add backfill button)

- [ ] **Step 1: Update ScrapeTrigger with backfill button**

Keep existing scrape + backfill buttons, add a new "Backfill All Sets" button that calls `POST /admin/backfill`:

```tsx
// frontend/src/components/ScrapeTrigger.tsx
"use client";

import { useState } from "react";

type ButtonState = "idle" | "loading" | "done" | "error";

function AdminButton({ label, endpoint }: { label: string; endpoint: string }) {
  const [state, setState] = useState<ButtonState>("idle");

  async function handle() {
    setState("loading");
    try {
      const r = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}${endpoint}`,
        { method: "POST" }
      );
      setState(r.ok ? "done" : "error");
    } catch {
      setState("error");
    }
    setTimeout(() => setState("idle"), 4000);
  }

  const labels: Record<ButtonState, string> = {
    idle: label, loading: "Starting…", done: "Started ✓", error: "Error ✗",
  };

  return (
    <button
      onClick={handle}
      disabled={state === "loading"}
      className={`px-3 py-1.5 text-xs rounded border transition-colors disabled:opacity-50 ${
        state === "done" ? "border-green-600 text-green-400" :
        state === "error" ? "border-red-600 text-red-400" :
        "border-gray-600 text-gray-400 hover:border-gray-400"
      }`}
    >
      {labels[state]}
    </button>
  );
}

export default function ScrapeTrigger() {
  return (
    <div className="flex gap-2 flex-wrap">
      <AdminButton label="Scrape now" endpoint="/admin/scrape" />
      <AdminButton label="Backfill history" endpoint="/admin/backfill" />
      <AdminButton label="Backfill Snkrdunk" endpoint="/admin/backfill/snkrdunk" />
    </div>
  );
}
```

- [ ] **Step 2: Commit all remaining changes and push**

```bash
git add -A
git status  # verify no secrets or large binaries
git commit -m "feat: complete dashboard rebuild — all sets, PSA pop, ATH, portfolio, themed backgrounds"
git push origin main
```

- [ ] **Step 3: After Render redeploys — trigger data population**

1. Visit `https://<backend-url>/admin/debug` — confirm `cards` and `snapshots` counts
2. POST `/admin/scrape` via the UI — populates current prices for all sets
3. POST `/admin/backfill` via the UI — runs Playwright backfill for historical prices + PSA pop (takes 10-30 min)
4. Refresh home page — top 50 trending cards should appear

- [ ] **Step 4: Verify the three pages work end-to-end**

- Home: cards with images, accent border, pop badge, all trend columns visible
- Detail: price panels with links, chart with range selector, pop count
- My Cards: add a card, verify P&L updates, remove it

---

## Self-Review Checklist

**Spec coverage:**
- ✅ All Pokemon sets — `discover_pokemon_sets()` scrapes PriceCharting category page
- ✅ PSA pop — scraped from PriceCharting, stored on `Card.psa_population`
- ✅ Sales velocity — `sales_per_day` on Card model and detail schema
- ✅ Historical prices (7d/30d/90d/1y) — `calculate_trend_vs_days_ago` with new 365-day variant
- ✅ ATH + % from ATH — `calculate_ath`, `calculate_pct_from_ath` in scoring.py
- ✅ Trend consistency — `calculate_trend_consistency` in scoring.py
- ✅ Image URL stored in DB — `fetch_card_image` called on card creation
- ✅ Accent colour from Pokemon type — `TYPE_COLORS` map + `accent_color` on Card
- ✅ Per-page background image — `layout.tsx` with `usePathname()`
- ✅ Home: top 50 upward trend, sortable — `GET /cards` with filter + sort param
- ✅ Detail: both prices + links, pop, ATH, chart with range — `GET /cards/{id}`
- ✅ My Cards: portfolio with P&L — `portfolio_items` table + `GET/POST/DELETE /portfolio`
- ✅ Snkrdunk secondary/pluggable — all Snkrdunk fields optional, dashboard works without it

**Type consistency check:** `_card_metrics` returns keys matching `CardSummary` fields. `_build_summary` spreads all metrics. `CardDetail` extends `CardSummary` — model_dump spread covers all base fields. `PortfolioItemOut` fields match `PortfolioTable` props. ✅
