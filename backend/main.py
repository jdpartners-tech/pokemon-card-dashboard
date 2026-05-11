from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import cards, watchlist, report

app = FastAPI(title="Pokemon Card Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(watchlist.router)
app.include_router(report.router)
