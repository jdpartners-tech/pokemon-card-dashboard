import logging
import re
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.pricecharting.com/",
}

# PriceCharting JSON API — returns products with grade-10 prices in cents
API_URL = "https://www.pricecharting.com/api/products"

# Pokemon sets to query (category IDs used by PriceCharting)
POKEMON_SETS = [
    "pokemon-base-set",
    "pokemon-jungle",
    "pokemon-fossil",
    "pokemon-team-rocket",
    "pokemon-neo-genesis",
    "pokemon-neo-revelation",
    "pokemon-neo-discovery",
    "pokemon-neo-destiny",
    "pokemon-gym-heroes",
    "pokemon-gym-challenge",
]


@dataclass
class ScrapedCard:
    name: str
    set_name: str
    card_number: str
    pricecharting_id: str
    psa10_price_usd: float


def scrape_pricecharting(max_pages: int = 10) -> list[ScrapedCard]:
    cards = []
    for set_id in POKEMON_SETS:
        try:
            batch = _scrape_set(set_id, max_pages)
            cards.extend(batch)
            logger.info(f"PriceCharting {set_id}: {len(batch)} cards")
        except Exception as e:
            logger.error(f"PriceCharting set {set_id} failed: {e}")
    logger.info(f"PriceCharting total: {len(cards)} cards")
    return cards


def _scrape_set(set_id: str, max_pages: int) -> list[ScrapedCard]:
    cards = []
    offset = 0
    limit = 100

    for _ in range(max_pages):
        params = {
            "id": set_id,
            "status": "collection",
            "grade": "10",
            "slabs": "psa",
            "offset": offset,
            "limit": limit,
        }
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()

        data = r.json()
        # API returns either a list or {"products": [...]}
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
        set_name = item.get("console-name") or item.get("set-name") or set_id.replace("-", " ").title()
        product_id = str(item.get("id") or "")

        # Prices stored in cents; grade-10 is PSA 10
        price_cents = item.get("grade-10") or item.get("psa-10-price") or 0
        if not price_cents or not name or not product_id:
            return None

        price_usd = price_cents / 100.0
        name_clean, card_number = _parse_name(name)

        return ScrapedCard(
            name=name_clean,
            set_name=set_name,
            card_number=card_number,
            pricecharting_id=product_id,
            psa10_price_usd=price_usd,
        )
    except Exception as e:
        logger.warning(f"PriceCharting product parse failed: {e}")
        return None


def _parse_name(full_name: str) -> tuple[str, str]:
    num_match = re.search(r"#(\S+)", full_name)
    card_number = num_match.group(1) if num_match else ""
    name = re.sub(r"#\S+", "", full_name).strip()
    return name, card_number
