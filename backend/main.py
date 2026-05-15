import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import cards, watchlist, report

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


@app.post("/admin/scrape", tags=["admin"])
async def trigger_scrape():
    """Manually trigger a scrape job (runs in background thread)."""
    import threading
    threading.Thread(target=run_scrape_job, daemon=True).start()
    return {"ok": True, "message": "Scrape job started in background"}
