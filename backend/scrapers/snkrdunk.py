import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try these URLs in order until one returns cards
CANDIDATE_URLS = [
    "https://snkrdunk.com/en/trading-cards/?keyword=pokemon&grade=PSA10",
    "https://snkrdunk.com/en/trading-cards/?keyword=pokemon",
    "https://snkrdunk.com/en/products/?category=trading-cards&keyword=pokemon",
    "https://snkrdunk.com/trading-cards/?keyword=pokemon&grade=PSA10",
]


@dataclass
class ScrapedCard:
    name: str
    set_name: str
    card_number: str
    snkrdunk_id: str
    psa10_price_hkd: float
    product_url: str = ""


def scrape_snkrdunk(max_pages: int = 20) -> list[ScrapedCard]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed — Snkrdunk scraping disabled")
        return []

    cards = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
            },
        )
        page = context.new_page()

        # Find which URL works
        base_url = _find_working_url(page)
        if not base_url:
            logger.error("Snkrdunk: no working URL found")
            browser.close()
            return cards

        for page_num in range(1, max_pages + 1):
            url = f"{base_url}&page={page_num}" if "?" in base_url else f"{base_url}?page={page_num}"
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                logger.warning(f"Snkrdunk page {page_num} load issue: {e}")

            items = _find_card_items(page)
            if not items:
                logger.info(f"Snkrdunk: no items on page {page_num}, stopping")
                break

            for item in items:
                card = _parse_item(item)
                if card:
                    cards.append(card)

            logger.info(f"Snkrdunk page {page_num}: {len(items)} items found")

        browser.close()

    logger.info(f"Snkrdunk total: {len(cards)} cards")
    return cards


def _find_working_url(page) -> str | None:
    for url in CANDIDATE_URLS:
        try:
            logger.info(f"Snkrdunk: trying {url}")
            resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")
            if resp and resp.status == 200:
                page.wait_for_load_state("networkidle", timeout=10000)
                items = _find_card_items(page)
                if items:
                    logger.info(f"Snkrdunk: working URL found: {url} ({len(items)} items)")
                    return url
                else:
                    logger.warning(f"Snkrdunk: {url} loaded but no items found")
        except Exception as e:
            logger.warning(f"Snkrdunk URL {url} failed: {e}")
    return None


ITEM_SELECTORS = [
    "[data-testid='card-item']",
    ".card-list-item",
    ".product-card",
    ".item-card",
    "li.product",
    ".trading-card-item",
    "[class*='CardItem']",
    "[class*='ProductCard']",
    "[class*='card-item']",
]

NAME_SELECTORS = [".card-name", ".product-name", "h3", "h2", "[class*='name']", "[class*='title']"]
PRICE_SELECTORS = [".price", ".card-price", "[data-price]", "[class*='price']", "[class*='Price']"]


def _find_card_items(page):
    for sel in ITEM_SELECTORS:
        items = page.query_selector_all(sel)
        if items:
            return items
    return []


def _parse_item(item) -> ScrapedCard | None:
    try:
        name_el = None
        for sel in NAME_SELECTORS:
            name_el = item.query_selector(sel)
            if name_el:
                break

        price_el = None
        for sel in PRICE_SELECTORS:
            price_el = item.query_selector(sel)
            if price_el:
                break

        link_el = item.query_selector("a")

        if not name_el or not price_el:
            return None

        full_name = name_el.inner_text().strip()
        price_text = (
            price_el.inner_text().strip()
            .replace("HK$", "").replace("HKD", "")
            .replace("$", "").replace(",", "").strip()
        )
        if not price_text:
            return None

        price = float(price_text)
        href = link_el.get_attribute("href") if link_el else ""
        snkrdunk_id = (href or "").strip("/").split("/")[-1] or full_name.lower().replace(" ", "-")
        product_url = f"https://snkrdunk.com{href}" if href and href.startswith("/") else ""

        name, set_name, card_number = _parse_name(full_name)

        return ScrapedCard(
            name=name,
            set_name=set_name,
            card_number=card_number,
            snkrdunk_id=snkrdunk_id,
            psa10_price_hkd=price,
            product_url=product_url,
        )
    except Exception as e:
        logger.warning(f"Snkrdunk item parse failed: {e}")
        return None


def _parse_name(full_name: str) -> tuple[str, str, str]:
    set_match = re.search(r"\[(.+?)\]", full_name)
    set_name = set_match.group(1) if set_match else "Unknown"
    num_match = re.search(r"#(\S+)", full_name)
    card_number = num_match.group(1) if num_match else ""
    name = re.sub(r"\[.+?\]", "", full_name).replace(f"#{card_number}", "").strip()
    return name, set_name, card_number
