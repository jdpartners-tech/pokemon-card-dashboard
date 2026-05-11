import logging
from dataclasses import dataclass
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

SNKRDUNK_HK_URL = "https://snkrdunk.com/en-hk/trading-cards/?keyword=pokemon&grade=PSA10"


@dataclass
class ScrapedCard:
    name: str
    set_name: str
    card_number: str
    snkrdunk_id: str
    psa10_price_hkd: float


def scrape_snkrdunk(max_pages: int = 20) -> list[ScrapedCard]:
    """Scrapes PSA 10 Pokemon card prices from snkrdunk HK."""
    cards = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for page_num in range(1, max_pages + 1):
            url = f"{SNKRDUNK_HK_URL}&page={page_num}"
            try:
                page.goto(url, timeout=30000)
                page.wait_for_selector("[data-testid='card-item'], .card-list-item, .product-card", timeout=10000)
            except Exception as e:
                logger.error(f"snkrdunk page {page_num} load failed: {e}")
                break

            items = page.query_selector_all("[data-testid='card-item'], .card-list-item, .product-card")
            if not items:
                break

            for item in items:
                try:
                    name_el = item.query_selector(".card-name, .product-name, h3")
                    price_el = item.query_selector(".price, .card-price, [data-price]")
                    link_el = item.query_selector("a")

                    if not name_el or not price_el:
                        continue

                    full_name = name_el.inner_text().strip()
                    name, set_name, card_number = _parse_name(full_name)
                    price_text = price_el.inner_text().strip().replace("HK$", "").replace(",", "").strip()
                    price = float(price_text)
                    href = link_el.get_attribute("href") if link_el else ""
                    snkrdunk_id = href.strip("/").split("/")[-1]

                    cards.append(ScrapedCard(
                        name=name,
                        set_name=set_name,
                        card_number=card_number,
                        snkrdunk_id=snkrdunk_id,
                        psa10_price_hkd=price,
                    ))
                except Exception as e:
                    logger.warning(f"snkrdunk item parse failed: {e}")
                    continue

        browser.close()

    return cards


def _parse_name(full_name: str) -> tuple[str, str, str]:
    import re
    set_match = re.search(r"\[(.+?)\]", full_name)
    set_name = set_match.group(1) if set_match else "Unknown"
    num_match = re.search(r"#(\S+)", full_name)
    card_number = num_match.group(1) if num_match else ""
    name = re.sub(r"\[.+?\]", "", full_name).replace(f"#{card_number}", "").strip()
    return name, set_name, card_number
