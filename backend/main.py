import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import cards, watchlist, report, portfolio

logging.basicConfig(level=logging.INFO)

DISABLE_SCHEDULER = os.getenv("DISABLE_SCHEDULER", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DISABLE_SCHEDULER:
        from backend.scheduler import create_scheduler, run_scrape_job
        scheduler = create_scheduler()
        scheduler.start()
        scheduler.add_job(run_scrape_job, id="scrape_on_startup", replace_existing=True)
        yield
        scheduler.shutdown(wait=False)
    else:
        yield


app = FastAPI(title="Pokemon Card Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(watchlist.router)
app.include_router(report.router)
app.include_router(portfolio.router)


@app.post("/admin/scrape", tags=["admin"])
async def trigger_scrape():
    """Manually trigger a scrape job (runs in background thread)."""
    from backend.scheduler import run_scrape_job
    import threading
    threading.Thread(target=run_scrape_job, daemon=True).start()
    return {"ok": True, "message": "Scrape job started in background"}


@app.post("/admin/backfill-images", tags=["admin"])
async def backfill_images():
    """Fetch image_url and accent_color from pokemontcg.io for all cards missing them."""
    import threading

    def _run():
        from backend.database import SessionLocal
        from backend.models import Card
        from backend.scrapers.pokemontcg import fetch_card_image
        db = SessionLocal()
        try:
            cards_missing = db.query(Card).filter(Card.image_url.is_(None)).all()
            logging.info(f"Backfilling images for {len(cards_missing)} cards")
            for card in cards_missing:
                try:
                    image_url, accent_color = fetch_card_image(card.name, card.card_number)
                    card.image_url = image_url
                    card.accent_color = accent_color
                    db.commit()
                except Exception as e:
                    logging.warning(f"Image fetch failed for {card.name}: {e}")
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "message": "Image backfill started in background"}


@app.post("/admin/backfill", tags=["admin"])
async def trigger_backfill():
    """Backfill full PSA 10 price history from PriceCharting for all cards (runs in background thread)."""
    import os, threading
    from fastapi import HTTPException
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured.")
    from backfill_history import run_backfill
    threading.Thread(target=run_backfill, args=(db_url,), daemon=True).start()
    return {"ok": True, "message": "Backfill started in background — this may take several minutes"}


@app.post("/admin/backfill/snkrdunk", tags=["admin"])
async def trigger_snkrdunk_backfill():
    """Backfill full PSA 10 price history from Snkrdunk for all cards (runs in background thread)."""
    import os, threading
    from fastapi import HTTPException
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured.")
    from backfill_snkrdunk import run_backfill
    threading.Thread(target=run_backfill, args=(db_url,), daemon=True).start()
    return {"ok": True, "message": "Snkrdunk backfill started in background — this may take several minutes"}


@app.get("/admin/debug", tags=["admin"])
async def debug_db():
    """Return snapshot counts and sample data to diagnose missing prices."""
    from backend.database import SessionLocal
    from backend.models import Card, PriceSnapshot
    from sqlalchemy import func
    db = SessionLocal()
    try:
        card_count = db.query(func.count(Card.id)).scalar()
        snap_count = db.query(func.count(PriceSnapshot.id)).scalar()
        snkr_count = db.query(func.count(PriceSnapshot.id)).filter(
            PriceSnapshot.snkrdunk_price_hkd.isnot(None)
        ).scalar()
        pc_count = db.query(func.count(PriceSnapshot.id)).filter(
            PriceSnapshot.pricecharting_price_hkd.isnot(None)
        ).scalar()
        # Sample the 5 most recent snapshots
        recent = db.query(PriceSnapshot).order_by(PriceSnapshot.scraped_at.desc()).limit(5).all()
        sample = [
            {
                "card_id": str(s.card_id),
                "scraped_at": s.scraped_at.isoformat() if s.scraped_at else None,
                "snkrdunk_price_hkd": float(s.snkrdunk_price_hkd) if s.snkrdunk_price_hkd else None,
                "pricecharting_price_hkd": float(s.pricecharting_price_hkd) if s.pricecharting_price_hkd else None,
            }
            for s in recent
        ]
        return {
            "cards": card_count,
            "snapshots_total": snap_count,
            "snapshots_with_snkrdunk": snkr_count,
            "snapshots_with_pricecharting": pc_count,
            "recent_snapshots": sample,
        }
    finally:
        db.close()
