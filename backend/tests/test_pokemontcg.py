from unittest.mock import patch, MagicMock
from backend.scrapers.pokemontcg import fetch_card_image, TYPE_COLORS

def test_type_colors_complete():
    for t in ["Fire", "Water", "Grass", "Psychic", "Lightning",
              "Fighting", "Dark", "Metal", "Dragon", "Fairy", "Colorless"]:
        assert t in TYPE_COLORS

def test_fetch_card_image_returns_url_and_color():
    mock_data = {
        "data": [{
            "images": {"small": "https://images.pokemontcg.io/base1/4.png"},
            "types": ["Fire"],
        }]
    }
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        url, color = fetch_card_image("Charizard", "4")
    assert url == "https://images.pokemontcg.io/base1/4.png"
    assert color == "#ef4444"  # Fire

def test_fetch_card_image_returns_none_on_empty():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        url, color = fetch_card_image("Unknown Card XYZ", None)
    assert url is None
    assert color == "#64748b"
