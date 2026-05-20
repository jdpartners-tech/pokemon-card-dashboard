# backend/scoring.py
from datetime import datetime, timezone, timedelta
from typing import Optional


def _aware_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get_price(snap) -> Optional[float]:
    if snap.pricecharting_price_hkd:
        return float(snap.pricecharting_price_hkd)
    if snap.snkrdunk_price_hkd:
        return float(snap.snkrdunk_price_hkd)
    return None


def calculate_trend_vs_days_ago(snapshots, days: int) -> Optional[float]:
    if not snapshots:
        return None
    sorted_snaps = sorted(snapshots, key=lambda s: _aware_dt(s.scraped_at), reverse=True)
    latest_price = _get_price(sorted_snaps[0])
    if not latest_price:
        return None
    latest_dt = _aware_dt(sorted_snaps[0].scraped_at)
    cutoff = latest_dt - timedelta(days=days)
    old_snaps = [s for s in snapshots if _aware_dt(s.scraped_at) <= cutoff]
    if not old_snaps:
        return None
    old_snap = max(old_snaps, key=lambda s: _aware_dt(s.scraped_at))
    # Reject baseline if it's more than [days] older than the cutoff — means we have
    # a data gap larger than the window itself, making the label (7D/30D/etc.) misleading.
    if (cutoff - _aware_dt(old_snap.scraped_at)).days > days:
        return None
    old_price = _get_price(old_snap)
    if not old_price or old_price == 0:
        return None
    return round((latest_price - old_price) / old_price * 100, 2)


def calculate_ath(snapshots) -> tuple[Optional[float], Optional[datetime]]:
    """Return (all-time-high price, date of that high)."""
    if not snapshots:
        return None, None
    best = max(snapshots, key=lambda s: _get_price(s) or 0)
    price = _get_price(best)
    if not price:
        return None, None
    return price, _aware_dt(best.scraped_at)


def calculate_trend_all_time(snapshots) -> Optional[float]:
    """% change from the very first snapshot to the latest."""
    if not snapshots:
        return None
    sorted_snaps = sorted(snapshots, key=lambda s: _aware_dt(s.scraped_at))
    first_price = _get_price(sorted_snaps[0])
    if not first_price or first_price == 0:
        return None
    latest_price = _get_price(sorted_snaps[-1])
    if not latest_price:
        return None
    return round((latest_price - first_price) / first_price * 100, 2)


def calculate_pct_from_ath(snapshots) -> Optional[float]:
    """% difference between current price and all-time high. Negative = below ATH."""
    if not snapshots:
        return None
    sorted_snaps = sorted(snapshots, key=lambda s: _aware_dt(s.scraped_at), reverse=True)
    current = _get_price(sorted_snaps[0])
    if not current:
        return None
    ath, _ = calculate_ath(snapshots)
    if not ath or ath == 0:
        return None
    return round((current - ath) / ath * 100, 2)


def calculate_trend_consistency(snapshots) -> int:
    """Count of weeks (out of last 4) where price rose. Returns 0-4."""
    if not snapshots:
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    for week in range(1, 5):
        end_dt = now - timedelta(weeks=week - 1)
        start_dt = now - timedelta(weeks=week)
        end_snaps = [s for s in snapshots if _aware_dt(s.scraped_at) <= end_dt]
        start_snaps = [s for s in snapshots if _aware_dt(s.scraped_at) <= start_dt]
        if not end_snaps or not start_snaps:
            continue
        end_price = _get_price(max(end_snaps, key=lambda s: _aware_dt(s.scraped_at)))
        start_price = _get_price(max(start_snaps, key=lambda s: _aware_dt(s.scraped_at)))
        if end_price and start_price and end_price > start_price:
            count += 1
    return count


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
            "card":      card,
            "trend_1m":  calculate_trend_vs_days_ago(snapshots, 30)  or 0.0,
            "trend_3m":  calculate_trend_vs_days_ago(snapshots, 90)  or 0.0,
            "arb_gap":   calculate_arbitrage(snapshots)               or 0.0,
            "volume":    float(len(snapshots)),
        })

    t1m_norm = _normalize([r["trend_1m"] for r in raw])
    t3m_norm = _normalize([r["trend_3m"] for r in raw])
    arb_norm = _normalize([r["arb_gap"]  for r in raw])
    vol_norm = _normalize([r["volume"]   for r in raw])

    results = []
    for i, r in enumerate(raw):
        score = (t1m_norm[i] * 0.40 + t3m_norm[i] * 0.30 + arb_norm[i] * 0.20 + vol_norm[i] * 0.10) * 100
        results.append({
            "card":     r["card"],
            "score":    round(score, 1),
            "trend_1m": r["trend_1m"],
            "trend_3m": r["trend_3m"],
            "arb_gap":  round(r["arb_gap"], 2),
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
