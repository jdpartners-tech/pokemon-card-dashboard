import requests
import logging
from bs4 import BeautifulSoup
from dataclasses import dataclass

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pricecharting.com"
POKEMON_CATEGORY_URL = f"{BASE_URL}/category/pokemon-cards?q=&sort=&grade=10&slabs=psa"


@dataclass
class ScrapedCard:
    name: str
    set_name: str
    card_number: str
    pricecharting_id: str
    psa10_price_usd: float


def scrape_pricecharting(max_pages: int = 10) -> list[ScrapedCard]:
    """Scrapes PSA 10 Pokemon card prices from pricecharting.com."""
    cards = []
    url = POKEMON_CATEGORY_URL

    for page in range(max_pages):
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"pricecharting page {page} failed: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table#games_table tbody tr")
        if not rows:
            break

        for row in rows:
            try:
                link_tag = row.select_one("td.title a")
                price_tag = row.select_one("td.price")
                if not link_tag or not price_tag:
                    continue

                href = link_tag["href"]
                pricecharting_id = href.strip("/").split("/")[-1]
                full_name = link_tag.get_text(strip=True)
                name, set_name, card_number = _parse_card_name(full_name)
                price_text = price_tag.get_text(strip=True).replace("$", "").replace(",", "")
                price = float(price_text)

                cards.append(ScrapedCard(
                    name=name,
                    set_name=set_name,
                    card_number=card_number,
                    pricecharting_id=pricecharting_id,
                    psa10_price_usd=price,
                ))
            except Exception as e:
                logger.warning(f"pricecharting row parse failed: {e}")
                continue

        next_link = soup.select_one("a.next-page")
        if not next_link:
            break
        url = BASE_URL + next_link["href"]

    return cards


def _parse_card_name(full_name: str) -> tuple[str, str, str]:
    """Best-effort parse of 'Charizard Holo [Base Set] #4' into (name, set, number)."""
    import re
    set_match = re.search(r"\[(.+?)\]", full_name)
    set_name = set_match.group(1) if set_match else "Unknown"
    num_match = re.search(r"#(\S+)", full_name)
    card_number = num_match.group(1) if num_match else ""
    name = re.sub(r"\[.+?\]", "", full_name).replace(f"#{card_number}", "").strip()
    return name, set_name, card_number
