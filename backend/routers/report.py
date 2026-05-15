import io
import csv
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from backend.database import get_db
from backend.models import Card, WatchlistItem
from backend.scoring import score_cards
from backend.routers.cards import _build_summary, _snap_in_window

router = APIRouter(prefix="/report", tags=["report"])


@router.get("")
def generate_report(db: Session = Depends(get_db)):
    watchlist_ids = {w.card_id for w in db.query(WatchlistItem).all()}
    cards = db.query(Card).all()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    card_snaps = [(c, [s for s in c.snapshots if _snap_in_window(s, cutoff)]) for c in cards]
    scored = score_cards(card_snaps)

    top_20 = scored[:20]
    watchlist_scored = [s for s in scored if s["card"].id in watchlist_ids]
    combined = {s["card"].id: s for s in top_20}
    for s in watchlist_scored:
        combined[s["card"].id] = s
    rows = sorted(combined.values(), key=lambda x: x["score"], reverse=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Set", "snkrdunk (HKD)", "PriceCharting (HKD)", "7-day %", "30-day %", "Arbitrage (HKD)", "Score"])

    for s in rows:
        summary = _build_summary(s, watchlist_ids)
        writer.writerow([
            summary.name,
            summary.set_name,
            f"{summary.snkrdunk_price_hkd:.0f}" if summary.snkrdunk_price_hkd else "",
            f"{summary.pricecharting_price_hkd:.0f}" if summary.pricecharting_price_hkd else "",
            f"{summary.trend_7d:+.1f}%",
            f"{summary.trend_30d:+.1f}%",
            f"{summary.arb_gap:.0f}",
            f"{summary.score:.1f}",
        ])

    output.seek(0)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pokemon-report-{date_str}.csv"},
    )
