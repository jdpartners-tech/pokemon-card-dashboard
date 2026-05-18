import logging
import re
import requests

logger = logging.getLogger(__name__)

TYPE_COLORS: dict[str, str] = {
    "Fire":       "#ef4444",
    "Water":      "#3b82f6",
    "Grass":      "#22c55e",
    "Psychic":    "#a855f7",
    "Lightning":  "#eab308",
    "Fighting":   "#f97316",
    "Dark":       "#7c3aed",
    "Metal":      "#94a3b8",
    "Dragon":     "#06b6d4",
    "Fairy":      "#ec4899",
    "Colorless":  "#64748b",
}

API_URL = "https://api.pokemontcg.io/v2/cards"


def _clean_name(name: str) -> str:
    """Strip edition/promo qualifiers like [1st Edition] or (Hidden Fates) for API lookup."""
    return re.sub(r'\s*[\[\(][^\]\)]*[\]\)]', '', name).strip()


def fetch_card_image(name: str, card_number: str | None) -> tuple[str | None, str]:
    """
    Query pokemontcg.io for the card image URL and derive accent colour from type.
    Returns (image_url, accent_color). image_url may be None; accent_color always has a value.
    Tries name+number first, falls back to name-only if no result.
    """
    try:
        clean = _clean_name(name)
        number = card_number.split("/")[0] if card_number else None

        queries = []
        if number:
            queries.append(f'name:"{clean}" number:{number}')
        queries.append(f'name:"{clean}"')

        for query in queries:
            resp = requests.get(
                API_URL,
                params={"q": query, "pageSize": 1},
                headers={"Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("data", [])
            card = results[0] if results else None
            if card:
                image_url = card.get("images", {}).get("small")
                types = card.get("types") or []
                accent = TYPE_COLORS.get(types[0], "#64748b") if types else "#64748b"
                return image_url, accent

        return None, "#64748b"
    except Exception as e:
        logger.warning(f"pokemontcg lookup failed for {name!r}: {e}")
        return None, "#64748b"
