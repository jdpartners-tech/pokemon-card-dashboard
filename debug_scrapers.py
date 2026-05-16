import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def debug_pricecharting():
    url = "https://www.pricecharting.com/category/pokemon-cards?q=&sort=&grade=10&slabs=psa"
    r = requests.get(url, headers=HEADERS, timeout=20)
    print(f"Status: {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")

    # Look for the table
    table = soup.find("table", id="games_table")
    print(f"Table #games_table: {table is not None}")

    # Find all tables
    tables = soup.find_all("table")
    print(f"Total tables: {len(tables)}")
    for t in tables:
        print(f"  id={t.get('id')} class={t.get('class')}")

    # Look for any product/card links
    links = soup.find_all("a", href=lambda h: h and "/game/" in h)
    print(f"Game links: {len(links)}")
    for l in links[:5]:
        print(f"  {l.text.strip()[:60]} -> {l['href']}")

def debug_snkrdunk():
    # Try to find the right URL by hitting the main site
    urls = [
        "https://snkrdunk.com/en/",
        "https://snkrdunk.com/en/trading-cards/",
        "https://snkrdunk.com/en/trading-cards/?keyword=pokemon",
    ]
    for url in urls:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"\n{url}")
        print(f"  Status: {r.status_code} | Final URL: {r.url}")
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        print(f"  Title: {title.text[:80] if title else 'none'}")
        # Look for card/product links
        links = soup.find_all("a", href=True)
        card_links = [l for l in links if "card" in l.get("href","").lower() or "pokemon" in l.get("href","").lower()]
        for l in card_links[:5]:
            print(f"  Link: {l.text.strip()[:40]} -> {l['href']}")

print("=== PriceCharting (requests) ===")
debug_pricecharting()
print("\n=== Snkrdunk ===")
debug_snkrdunk()
