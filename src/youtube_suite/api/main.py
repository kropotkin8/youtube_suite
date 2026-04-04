from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from youtube_suite.api.routers import insights, jobs, market, studio

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

app = FastAPI(
    title="Creator Intel Platform",
    description="Market (YouTube ETL) + Studio (subs, descriptions) + Shorts jobs",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
app.include_router(studio.router)
app.include_router(jobs.router)
app.include_router(insights.router)


@app.get("/")
def root() -> dict:
    """Return service metadata and available router prefixes."""
    return {
        "service": "creator-intel-platform",
        "docs": "/docs",
        "routers": ["/market", "/studio", "/jobs", "/insights"],
    }
