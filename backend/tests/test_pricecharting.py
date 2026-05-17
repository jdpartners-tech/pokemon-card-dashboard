from unittest.mock import patch, MagicMock
from backend.scrapers.pricecharting import discover_pokemon_sets, scrape_pricecharting


def test_discover_sets_returns_list_of_strings():
    mock_html = """
    <html><body>
      <a href="/category/pokemon-base-set">Base Set</a>
      <a href="/category/pokemon-scarlet-violet">Scarlet &amp; Violet</a>
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
