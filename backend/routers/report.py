import io
import csv
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.database import get_db
from backend.models import Card, WatchlistItem
from backend.routers.cards import _build_summary, _card_metrics

router = APIRouter(prefix="/report", tags=["report"])


@router.get("")
def generate_report(db: Session = Depends(get_db)):
    watchlist_ids = {w.card_id for w in db.query(WatchlistItem).all()}
    cards = db.query(Card).all()

    results = []
    for card in cards:
        metrics = _card_metrics(card.snapshots)
        results.append((card, metrics))

    # Report: watchlist cards first, then all others sorted by 7d trend
    watchlist_results = [(c, m) for c, m in results if c.id in watchlist_ids]
    other_results = [(c, m) for c, m in results if c.id not in watchlist_ids]
    other_results.sort(key=lambda x: x[1]["trend_1m"] or float("-inf"), reverse=True)

    rows = watchlist_results + other_results[:20]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Set", "Snkrdunk (HKD)", "PriceCharting (HKD)", "1M %", "3M %", "6M %", "All %"])

    for card, metrics in rows:
        summary = _build_summary(card, metrics, watchlist_ids)
        writer.writerow([
            summary.name,
            summary.set_name,
            f"{summary.snkrdunk_price_hkd:.0f}" if summary.snkrdunk_price_hkd else "",
            f"{summary.pricecharting_price_hkd:.0f}" if summary.pricecharting_price_hkd else "",
            f"{summary.trend_1m:+.1f}%" if summary.trend_1m is not None else "",
            f"{summary.trend_3m:+.1f}%" if summary.trend_3m is not None else "",
            f"{summary.trend_6m:+.1f}%" if summary.trend_6m is not None else "",
            f"{summary.trend_all:+.1f}%" if summary.trend_all is not None else "",
        ])

    output.seek(0)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pokemon-report-{date_str}.csv"},
    )
