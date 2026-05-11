from datetime import datetime, timezone, timedelta
from typing import Optional


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    min_v, max_v = min(values), max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]


def calculate_price_trend(snapshots, days: int) -> Optional[float]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    prev_cutoff = now - timedelta(days=days * 2)

    recent = [s for s in snapshots if s.scraped_at >= cutoff]
    prev = [s for s in snapshots if prev_cutoff <= s.scraped_at < cutoff]

    def avg_prices(snaps):
        prices = []
        for s in snaps:
            if s.snkrdunk_price_hkd:
                prices.append(float(s.snkrdunk_price_hkd))
            if s.pricecharting_price_hkd:
                prices.append(float(s.pricecharting_price_hkd))
        return sum(prices) / len(prices) if prices else None

    r_avg = avg_prices(recent)
    p_avg = avg_prices(prev)
    if r_avg is None or p_avg is None or p_avg == 0:
        return None
    return (r_avg - p_avg) / p_avg * 100


def calculate_arbitrage(snapshots) -> Optional[float]:
    if not snapshots:
        return None
    latest = max(snapshots, key=lambda s: s.scraped_at)
    if latest.snkrdunk_price_hkd and latest.pricecharting_price_hkd:
        return abs(float(latest.snkrdunk_price_hkd) - float(latest.pricecharting_price_hkd))
    return None


def score_cards(card_snapshots: list[tuple]) -> list[dict]:
    """
    Args: list of (Card, list[PriceSnapshot])
    Returns: list of score dicts sorted by score descending
    """
    raw = []
    for card, snapshots in card_snapshots:
        raw.append({
            "card": card,
            "trend_7d": calculate_price_trend(snapshots, 7) or 0.0,
            "trend_30d": calculate_price_trend(snapshots, 30) or 0.0,
            "arb_gap": calculate_arbitrage(snapshots) or 0.0,
            "volume": float(len(snapshots)),
        })

    t7_norm = _normalize([r["trend_7d"] for r in raw])
    t30_norm = _normalize([r["trend_30d"] for r in raw])
    arb_norm = _normalize([r["arb_gap"] for r in raw])
    vol_norm = _normalize([r["volume"] for r in raw])

    results = []
    for i, r in enumerate(raw):
        score = (t7_norm[i] * 0.40 + t30_norm[i] * 0.30 + arb_norm[i] * 0.20 + vol_norm[i] * 0.10) * 100
        results.append({
            "card": r["card"],
            "score": round(score, 1),
            "trend_7d": round(r["trend_7d"], 2),
            "trend_30d": round(r["trend_30d"], 2),
            "arb_gap": round(r["arb_gap"], 2),
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
