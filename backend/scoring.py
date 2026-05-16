from datetime import datetime, timezone, timedelta
from typing import Optional


def _aware_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get_price(snap) -> Optional[float]:
    """Return the best available price from a snapshot (prefer snkrdunk, fall back to pricecharting)."""
    if snap.snkrdunk_price_hkd:
        return float(snap.snkrdunk_price_hkd)
    if snap.pricecharting_price_hkd:
        return float(snap.pricecharting_price_hkd)
    return None


def calculate_trend_vs_days_ago(snapshots, days: int) -> Optional[float]:
    """
    % change: latest price vs the most recent snapshot that is at least `days` old.
    Works well with monthly data — finds the closest available historical point.
    """
    if not snapshots:
        return None

    sorted_snaps = sorted(snapshots, key=lambda s: _aware_dt(s.scraped_at), reverse=True)
    latest = sorted_snaps[0]
    latest_price = _get_price(latest)
    if not latest_price:
        return None

    latest_dt = _aware_dt(latest.scraped_at)
    cutoff = latest_dt - timedelta(days=days)

    # snapshots strictly older than `days` ago
    old_snaps = [s for s in snapshots if _aware_dt(s.scraped_at) <= cutoff]
    if not old_snaps:
        return None

    # Pick the most recent one (closest to `days` ago)
    old_snap = max(old_snaps, key=lambda s: _aware_dt(s.scraped_at))
    old_price = _get_price(old_snap)
    if not old_price or old_price == 0:
        return None

    return round((latest_price - old_price) / old_price * 100, 2)


def calculate_arbitrage(snapshots) -> Optional[float]:
    if not snapshots:
        return None
    latest = max(snapshots, key=lambda s: _aware_dt(s.scraped_at))
    if latest.snkrdunk_price_hkd and latest.pricecharting_price_hkd:
        return abs(float(latest.snkrdunk_price_hkd) - float(latest.pricecharting_price_hkd))
    return None


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    min_v, max_v = min(values), max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]


def score_cards(card_snapshots: list[tuple]) -> list[dict]:
    """
    Args: list of (Card, list[PriceSnapshot]) — pass ALL snapshots per card.
    Returns: list of score dicts sorted by score descending.
    """
    raw = []
    for card, snapshots in card_snapshots:
        raw.append({
            "card": card,
            "trend_7d":  calculate_trend_vs_days_ago(snapshots, 7)  or 0.0,
            "trend_30d": calculate_trend_vs_days_ago(snapshots, 30) or 0.0,
            "trend_90d": calculate_trend_vs_days_ago(snapshots, 90) or 0.0,
            "arb_gap":   calculate_arbitrage(snapshots)             or 0.0,
            "volume":    float(len(snapshots)),
        })

    t7_norm  = _normalize([r["trend_7d"]  for r in raw])
    t30_norm = _normalize([r["trend_30d"] for r in raw])
    arb_norm = _normalize([r["arb_gap"]   for r in raw])
    vol_norm = _normalize([r["volume"]    for r in raw])

    results = []
    for i, r in enumerate(raw):
        score = (t7_norm[i] * 0.40 + t30_norm[i] * 0.30 + arb_norm[i] * 0.20 + vol_norm[i] * 0.10) * 100
        results.append({
            "card":      r["card"],
            "score":     round(score, 1),
            "trend_7d":  r["trend_7d"],
            "trend_30d": r["trend_30d"],
            "trend_90d": r["trend_90d"],
            "arb_gap":   round(r["arb_gap"], 2),
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
