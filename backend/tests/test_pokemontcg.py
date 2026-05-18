from unittest.mock import patch, MagicMock, call
from backend.scrapers.pokemontcg import fetch_card_image, TYPE_COLORS, _clean_name

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


def test_clean_name_strips_edition_qualifiers():
    assert _clean_name("Mewtwo [1st Edition]") == "Mewtwo"
    assert _clean_name("Charizard (Hidden Fates)") == "Charizard"
    assert _clean_name("Pikachu [Shadowless]") == "Pikachu"
    assert _clean_name("Lugia") == "Lugia"


def test_fetch_card_image_strips_qualifier_from_name():
    mock_data = {
        "data": [{
            "images": {"small": "https://images.pokemontcg.io/base1/10.png"},
            "types": ["Psychic"],
        }]
    }
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        url, color = fetch_card_image("Mewtwo [1st Edition]", "10")
    assert url == "https://images.pokemontcg.io/base1/10.png"
    # The query should use clean name "Mewtwo", not "Mewtwo [1st Edition]"
    called_params = mock_get.call_args[1]["params"]["q"]
    assert "Mewtwo [1st Edition]" not in called_params
    assert "Mewtwo" in called_params


def test_fetch_card_image_falls_back_to_name_only():
    """If name+number returns nothing, falls back to name-only query."""
    empty = {"data": []}
    found = {"data": [{"images": {"small": "https://images.pokemontcg.io/neo4/9.png"}, "types": ["Colorless"]}]}
    with patch("requests.get") as mock_get:
        resp_empty = MagicMock()
        resp_empty.json.return_value = empty
        resp_empty.raise_for_status.return_value = None
        resp_found = MagicMock()
        resp_found.json.return_value = found
        resp_found.raise_for_status.return_value = None
        mock_get.side_effect = [resp_empty, resp_found]
        url, color = fetch_card_image("Lugia", "9")
    assert url == "https://images.pokemontcg.io/neo4/9.png"
    assert mock_get.call_count == 2
