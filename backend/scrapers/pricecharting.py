import logging
from dataclasses import dataclass
from playwright.sync_api import sync_playwright

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
    """Scrapes PSA 10 Pokemon card prices from pricecharting.com using Playwright."""
    cards = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = POKEMON_CATEGORY_URL

        for page_num in range(max_pages):
            try:
                page.goto(url, timeout=30000)
                page.wait_for_selector("table#games_table tbody tr", timeout=15000)
            except Exception as e:
                logger.error(f"pricecharting page {page_num} load failed: {e}")
                break

            rows = page.query_selector_all("table#games_table tbody tr")
            if not rows:
                break

            for row in rows:
                try:
                    link_el = row.query_selector("td.title a")
                    price_el = row.query_selector("td.price")
                    if not link_el or not price_el:
                        continue

                    href = link_el.get_attribute("href") or ""
                    pricecharting_id = href.strip("/").split("/")[-1]
                    full_name = link_el.inner_text().strip()
                    name, set_name, card_number = _parse_card_name(full_name)
                    price_text = price_el.inner_text().strip().replace("$", "").replace(",", "")
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

            next_el = page.query_selector("a.next-page")
            if not next_el:
                break
            next_href = next_el.get_attribute("href")
            if not next_href:
                break
            url = BASE_URL + next_href

        browser.close()

    return cards


def _parse_card_name(full_name: str) -> tuple[str, str, str]:
    import re
    set_match = re.search(r"\[(.+?)\]", full_name)
    set_name = set_match.group(1) if set_match else "Unknown"
    num_match = re.search(r"#(\S+)", full_name)
    card_number = num_match.group(1) if num_match else ""
    name = re.sub(r"\[.+?\]", "", full_name).replace(f"#{card_number}", "").strip()
    return name, set_name, card_number
