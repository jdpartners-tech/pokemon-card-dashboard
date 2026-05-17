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
            m = re.match(r"^/(?:category|console)/(pokemon-[^/?#]+)", href)
            if m:
                slug = m.group(1)
                if slug not in slugs:
                    slugs.append(slug)
        logger.info(f"Discovered {len(slugs)} Pokemon sets from PriceCharting")
        return slugs
    except Exception as e:
        logger.error(f"Failed to discover sets: {e}")
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

        price_hkd = item.get("grade-10-hkd") or item.get("psa-10-price-hkd")
        if not price_hkd:
            price_cents = item.get("grade-10") or item.get("psa-10-price") or 0
            if not price_cents:
                return None
            price_hkd = price_cents / 100.0 * 7.8

        if not name or not product_id:
            return None

        name_clean, card_number = _parse_name(name)
        pc_url = f"https://www.pricecharting.com/game/{set_id}/{name_clean.lower().replace(' ', '-')}-{card_number}"

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
