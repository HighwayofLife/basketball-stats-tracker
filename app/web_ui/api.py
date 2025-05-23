# pylint: disable=singleton-comparison
"""FastAPI application for Basketball Stats Tracker."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import admin_router, games_router, pages_router, players_router, teams_router

# Configure logger
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Basketball Stats Tracker",
    description="API for basketball statistics and analytics",
    version="0.1.0",
)

# Setup static files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include routers
app.include_router(pages_router)
app.include_router(games_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(admin_router)
