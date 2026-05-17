"""
Snkrdunk PSA 10 price history scraper.

Two-phase approach:
  1. collect_product_urls()  — scrapes listing pages, returns (ScrapedCard, product_url) pairs
  2. fetch_psa10_history()   — visits each product page, intercepts JSON API calls,
                               extracts historical PSA 10 prices
"""
import logging
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, Page
from backend.scrapers.snkrdunk import ScrapedCard, CANDIDATE_URLS, ITEM_SELECTORS, _find_card_items, _parse_item, _find_working_url

logger = logging.getLogger(__name__)


# ── Phase 1: collect product URLs from listing pages ─────────────────────────

def collect_product_urls(max_pages: int = 20) -> list[tuple[ScrapedCard, str]]:
    """
    Scrape listing pages and return (ScrapedCard, product_url) pairs.
    Only includes cards where a real product URL was captured.
    """
    results: list[tuple[ScrapedCard, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = context.new_page()

        base_url = _find_working_url(page)
        if not base_url:
            logger.error("Snkrdunk: no working URL found for listing")
            browser.close()
            return results

        for page_num in range(1, max_pages + 1):
            url = f"{base_url}&page={page_num}" if "?" in base_url else f"{base_url}?page={page_num}"
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                logger.warning(f"Listing page {page_num} load issue: {e}")

            items = _find_card_items(page)
            if not items:
                logger.info(f"Snkrdunk listing: no items on page {page_num}, stopping")
                break

            for item in items:
                card = _parse_item(item)
                if card and card.product_url:
                    results.append((card, card.product_url))

            logger.info(f"Snkrdunk listing page {page_num}: {len(items)} items, {sum(1 for _, u in results if u)} with URLs so far")

        browser.close()

    logger.info(f"Collected {len(results)} cards with product URLs")
    return results


# ── Phase 2: fetch price history from product pages ──────────────────────────

def fetch_psa10_history_batch(product_urls: list[str]) -> dict[str, list[tuple[datetime, float]]]:
    """
    Visit each product URL and extract PSA 10 price history.
    Returns {product_url: [(datetime_utc, hkd_price), ...]}.
    """
    results: dict[str, list[tuple[datetime, float]]] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9", "Accept": "text/html,*/*"},
        )
        page = context.new_page()

        for url in product_urls:
            logger.info(f"Fetching history: {url}")
            points = _fetch_single(page, url)
            results[url] = points
            logger.info(f"  → {len(points)} PSA 10 data points")

        browser.close()

    return results


def _fetch_single(page: Page, url: str) -> list[tuple[datetime, float]]:
    captured_responses: list[tuple[str, object]] = []

    def on_response(response):
        if response.status != 200:
            return
        ct = response.headers.get("content-type", "")
        if "json" not in ct:
            return
        try:
            captured_responses.append((response.url, response.json()))
        except Exception:
            pass

    page.on("response", on_response)
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
    except Exception as e:
        logger.warning(f"  Page load issue: {e}")
    finally:
        page.remove_listener("response", on_response)

    # Try each captured JSON response
    for resp_url, data in captured_responses:
        points = _try_parse(resp_url, data)
        if points:
            return points

    # Fallback: JavaScript chart extraction
    return _try_js_extraction(page)


# ── Parsers ───────────────────────────────────────────────────────────────────

def _try_parse(resp_url: str, data) -> list[tuple[datetime, float]]:
    """Try multiple JSON shapes to find PSA 10 price history."""
    if isinstance(data, list):
        points = _parse_array(data, resp_url)
        if points:
            return points

    if isinstance(data, dict):
        for key in ("price_histories", "price_history", "histories", "prices", "items", "records"):
            if key in data:
                points = _parse_array(data[key], resp_url)
                if points:
                    return points

        nested = data.get("data")
        if isinstance(nested, list):
            points = _parse_array(nested, resp_url)
            if points:
                return points
        if isinstance(nested, dict):
            for key in ("price_histories", "price_history", "histories", "prices"):
                if key in nested:
                    points = _parse_array(nested[key], resp_url)
                    if points:
                        return points

    return []


def _parse_array(items, resp_url: str) -> list[tuple[datetime, float]]:
    if not isinstance(items, list) or not items:
        return []

    points: list[tuple[datetime, float]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        # Skip non-PSA-10 entries when grade information is present
        grade = (
            item.get("grade") or item.get("slab_grade") or
            item.get("evaluation") or item.get("grading")
        )
        if grade is not None:
            g = str(grade).upper().replace(" ", "").replace("-", "")
            if g not in ("PSA10", "10"):
                continue

        dt = _parse_date_field(item)
        if dt is None:
            continue

        price = _parse_price_field(item)
        if price is None or price <= 0:
            continue

        points.append((dt, price))

    if points:
        logger.debug(f"  Parsed {len(points)} points from {resp_url}")
    return points


def _parse_date_field(item: dict) -> datetime | None:
    for key in ("date", "traded_at", "created_at", "sold_at", "at", "timestamp", "time", "datetime"):
        val = item.get(key)
        if not val:
            continue
        try:
            return _parse_date(val)
        except Exception:
            pass
    return None


def _parse_price_field(item: dict) -> float | None:
    for key in ("price", "hkd_price", "amount", "value", "sold_price", "trade_price"):
        val = item.get(key)
        if val is None:
            continue
        try:
            return float(val)
        except Exception:
            pass
    return None


def _parse_date(val) -> datetime:
    if isinstance(val, (int, float)):
        # Unix timestamp — try ms then s
        ts = val / 1000 if val > 1e10 else val
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    s = str(val).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            pass
    # ISO 8601 with timezone offset (Python 3.11+)
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc) if "+" not in s else datetime.fromisoformat(s)


# ── JavaScript fallbacks ──────────────────────────────────────────────────────

def _try_js_extraction(page: Page) -> list[tuple[datetime, float]]:
    # Try Highcharts (same approach as PriceCharting backfill)
    try:
        series = page.evaluate("""
            () => {
                if (typeof Highcharts === 'undefined') return null;
                const chart = Highcharts.charts.find(c => c);
                if (!chart) return null;
                return chart.series.map(s => ({
                    name: s.name || '',
                    data: s.data
                        .filter(p => p && p.y != null && p.y > 0)
                        .map(p => [p.x, p.y])
                }));
            }
        """)
        if series:
            # Prefer a series named "PSA 10" or "PSA10"; fall back to first
            psa10 = next(
                (s for s in series if re.search(r"psa.?10", s["name"], re.I)),
                series[0] if series else None,
            )
            if psa10:
                points = [
                    (datetime.fromtimestamp(x / 1000, tz=timezone.utc), float(y))
                    for x, y in psa10["data"]
                    if y and y > 0
                ]
                if points:
                    logger.debug(f"  Extracted {len(points)} points via Highcharts JS")
                    return points
    except Exception as e:
        logger.debug(f"  Highcharts extraction failed: {e}")

    # Try Nuxt/Vue embedded state
    try:
        state = page.evaluate("() => window.__NUXT__ ? JSON.stringify(window.__NUXT__) : null")
        if state:
            import json
            data = json.loads(state)
            points = _search_nested_for_prices(data)
            if points:
                logger.debug(f"  Extracted {len(points)} points from __NUXT__ state")
                return points
    except Exception as e:
        logger.debug(f"  NUXT state extraction failed: {e}")

    return []


def _search_nested_for_prices(obj, depth: int = 0) -> list[tuple[datetime, float]]:
    """Recursively search a JSON object for arrays that look like price history."""
    if depth > 8:
        return []
    if isinstance(obj, list) and len(obj) >= 3:
        points = _parse_array(obj, "<embedded>")
        if points:
            return points
    if isinstance(obj, dict):
        for key in ("price_histories", "price_history", "histories", "prices", "priceHistories"):
            if key in obj:
                points = _parse_array(obj[key], f"<embedded.{key}>")
                if points:
                    return points
        for v in obj.values():
            if isinstance(v, (dict, list)):
                points = _search_nested_for_prices(v, depth + 1)
                if points:
                    return points
    return []
