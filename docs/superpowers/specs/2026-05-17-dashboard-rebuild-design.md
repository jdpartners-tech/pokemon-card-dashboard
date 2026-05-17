# Pokemon Card Dashboard — Rebuild Design

**Date:** 2026-05-17  
**Status:** Approved  

---

## Goal

A personal investment dashboard for tracking PSA 10 graded Pokemon cards. The primary question it answers: **which PSA 10 cards have an upward price trend and are worth buying?**

---

## Scope

- All Pokemon sets (not just vintage) — covers the full investable universe on PriceCharting
- PSA 10 grade only throughout
- Three pages: Home (top 50 trending), Card Detail, My Cards (portfolio tracker)
- HKD only for all prices
- Snkrdunk is a secondary source; dashboard is fully functional without it

---

## Data Pipeline

### Primary source: PriceCharting

PriceCharting provides a JSON API (`https://www.pricecharting.com/api/products`) that covers all Pokemon sets with PSA 10 prices in HKD. This is the source of truth for:

- Card discovery (what cards exist across all sets)
- Current PSA 10 prices
- Historical price data (scraped from Highcharts JS on each product page)
- PSA population (Grade 10 count, scraped from the pop report section of each product page)
- Sales velocity ("X sales per day", scraped from each product page)
- PriceCharting product page URL (stored per card)

**Historical backfill:** A one-time admin-triggered backfill visits each card's PriceCharting product page via Playwright, evaluates the Highcharts JS object, and extracts monthly PSA 10 price data points going back up to 1 year. These are inserted as `PriceSnapshot` rows with their original historical dates.

**Ongoing scrape:** APScheduler runs every 6 hours to capture current prices and insert new snapshots.

### Secondary source: Snkrdunk

Snkrdunk provides HKD prices natively. It is scraped best-effort via Playwright. When available, the current Snkrdunk price and product URL are stored per card. The Snkrdunk scraper can be fixed/replaced independently without affecting any other part of the system.

### Card images

On first card creation, the pokemontcg.io API is queried once for the card image URL and a dominant accent color (extracted from the image). Both are stored in the `cards` table. All subsequent page loads read from the DB — no external API call at render time.

---

## Database Schema

### `cards` table (additions to existing schema)

| Column | Type | Description |
|---|---|---|
| `image_url` | String | pokemontcg.io image URL |
| `accent_color` | String | Hex color extracted from card art (e.g. `#f59e0b`) |
| `snkrdunk_url` | String | Full Snkrdunk product page URL |
| `pricecharting_url` | String | Full PriceCharting product page URL |
| `psa_population` | Integer | PSA 10 graded population count |
| `sales_per_day` | Float | Average PSA 10 sales per day (from PriceCharting) |

### `price_snapshots` table — unchanged

Existing columns (`snkrdunk_price_hkd`, `pricecharting_price_hkd`, `scraped_at`) cover all needs. Historical backfill data is inserted as snapshots with original historical dates.

### `portfolio_items` table (new)

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `card_id` | UUID | FK → cards |
| `purchase_price_hkd` | Numeric(12,2) | What the user paid |
| `purchased_at` | Date | Purchase date |
| `added_at` | DateTime | When the record was created |

### `watchlist` table — unchanged

---

## Computed Metrics

All computed at query time from `price_snapshots`, not stored.

| Metric | Definition |
|---|---|
| `trend_7d` | % change: latest price vs most recent snapshot ≥ 7 days old |
| `trend_30d` | % change: latest price vs most recent snapshot ≥ 30 days old |
| `trend_90d` | % change: latest price vs most recent snapshot ≥ 90 days old |
| `trend_1y` | % change: latest price vs most recent snapshot ≥ 365 days old |
| `ath` | All-time high price across all snapshots |
| `ath_date` | Date of that all-time high |
| `pct_from_ath` | `(current - ath) / ath * 100` (negative = below ATH) |
| `trend_consistency` | Count of weeks (out of last 4) where week-end price > week-start price |

For trend calculations, the "latest price" prefers `pricecharting_price_hkd`; falls back to `snkrdunk_price_hkd`.

---

## Backend API

### `GET /cards`

Returns cards with a **positive `trend_30d`** (upward trending), sorted descending by the `sort` param.

Query params:
- `sort` — `trend_7d` | `trend_30d` (default) | `trend_90d` | `trend_1y`
- `search` — filter by card name (case-insensitive)
- `limit` — default 50

Response fields per card: `id`, `name`, `set_name`, `card_number`, `image_url`, `accent_color`, `snkrdunk_price_hkd`, `pricecharting_price_hkd`, `psa_population`, `trend_7d`, `trend_30d`, `trend_90d`, `trend_1y`, `pct_from_ath`, `trend_consistency`, `in_watchlist`.

### `GET /cards/{id}`

Full card detail. Adds: `snkrdunk_url`, `pricecharting_url`, `sales_per_day`, `ath`, `ath_date`, `history` (list of `{date, snkrdunk_price_hkd, pricecharting_price_hkd}` sorted oldest→newest).

### `GET /portfolio`

Returns all portfolio items with computed current value and P&L. Also returns portfolio-level totals: `total_invested`, `total_current_value`, `total_pnl_hkd`, `total_pnl_pct`.

### `POST /portfolio`

Body: `{ card_id, purchase_price_hkd, purchased_at }`. Adds a card to the portfolio. A card can be added multiple times (multiple purchases).

### `DELETE /portfolio/{id}`

Removes a single portfolio item by its `id`.

### Existing endpoints — unchanged

`GET /watchlist`, `POST /watchlist`, `DELETE /watchlist/{card_id}`, `GET /report`, `POST /admin/scrape`, `POST /admin/backfill`, `GET /admin/debug`.

---

## Frontend — Pages & Components

### Theme

Deep midnight background (`#0a0a1f`) with zinc-tinted row alternation. Each card row has a coloured left-border accent derived from the card's `accent_color` field (extracted from card art). Green for positive trends, red for negative.

### Home Page (`/`)

**Header:** "Top Trending PSA 10 Cards" · card count · active sort label.  
**Toolbar:** search input, sort selector (7d / 30d / 90d / 1y).

**Table columns (left → right):**
1. Watchlist toggle (☆/★)
2. Card thumbnail (56×78px, from `image_url`, left-border accent)
3. Card name (full name line 1, set code + set name line 2, Pop badge + trend consistency below)
4. Price HKD (source: Snkrdunk or PriceCharting label)
5. vs ATH (amber if within 10%, red if more than 10% below)
6. 7d trend
7. 30d trend (default sort — bold, blue header)
8. 90d trend
9. 1y trend

Clicking any row navigates to the card detail page.

### Card Detail Page (`/card/[id]`)

**Header section:** large card image (left), card name + set, PSA 10 badge, Pop count, sales/day, trend consistency, % from ATH with ATH value and date, watchlist button.

**Price comparison:** two side-by-side panels — Snkrdunk (HKD) with "View on Snkrdunk ↗" link, PriceCharting (HKD) with "View on PriceCharting ↗" link.

**Trend stats:** four tiles — 7d, 30d (highlighted), 90d, 1y.

**Price history chart:** line chart with 6m / 1y / All time range selector. Two series: PriceCharting (solid line) and Snkrdunk (dashed line, when available).

**PSA population bar chart:** grade distribution (1–10) from PriceCharting pop data, with Grade 10 count called out.

### My Cards Page (`/my-cards`)

**Summary bar:** Cards Owned · Total Invested · Current Value · Total P&L (HKD + %).

**Table columns:** thumbnail + name + pop | Purchase date | Paid (HKD) | Now (HKD) | P&L (HKD + %) | 30d trend | Remove.  
Default sort: P&L % descending.

**Add Card:** button opens a modal with card search (autocomplete from DB), purchase price (HKD), and purchase date fields.

### Navigation

Top nav bar: **Home** | **My Cards** | **Watchlist** (existing). 

---

## Image & Accent Color Pipeline

On first card creation (during scrape or backfill):

1. Query `https://api.pokemontcg.io/v2/cards?q=name:"..." number:{card_number}&pageSize=1`
2. Store `images.small` URL as `image_url`
3. Read the `types[]` field from the response and map to a fixed accent color:
   - Fire → `#ef4444`, Water → `#3b82f6`, Grass → `#22c55e`, Psychic → `#a855f7`
   - Lightning → `#eab308`, Fighting → `#f97316`, Dark → `#7c3aed`, Metal → `#94a3b8`
   - Dragon → `#06b6d4`, Fairy → `#ec4899`, Colorless / Unknown → `#64748b`
4. Store the mapped hex as `accent_color`

If pokemontcg.io returns no result, `image_url` is null and `accent_color` defaults to `#64748b` (slate grey); the UI shows a grey placeholder with no accent border.

---

## Error States

- **No snapshot data:** price cells show "—"; trend cells show "—"; card still appears in list (cannot sort by trend, excluded from trending-only home page filter).
- **Snkrdunk unavailable:** Snkrdunk price panel shows "Not available" with the link still shown if URL is stored.
- **Image not found:** grey card-shaped placeholder, no accent border.
- **Portfolio card deleted from DB:** portfolio item shows card name as stored text, prices as "—".

---

## What Is NOT in Scope

- User authentication (single-user personal tool)
- Multiple currencies or FX conversion
- CGC or other grading companies
- Price alerts or notifications
- Mobile-specific layout (responsive enough to read, not optimized)
- Snkrdunk historical data (current price only, history from PriceCharting)
