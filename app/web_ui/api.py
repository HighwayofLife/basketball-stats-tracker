# pylint: disable=singleton-comparison
"""FastAPI application for Basketball Stats Tracker."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import VERSION_INFO

from .routers import admin_router, auth_router, games_router, pages_router, players_router, reports_router, teams_router

# Configure logger
logger = logging.getLogger(__name__)


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle proxy headers from Cloud Run."""

    async def dispatch(self, request: Request, call_next):
        # Check if we're behind a proxy (Cloud Run)
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto == "https":
            # Force the request URL to be HTTPS
            request.scope["scheme"] = "https"

        response = await call_next(request)
        return response


# Import version info
from app.config import VERSION_INFO

# Create FastAPI application
app = FastAPI(
    title="Basketball Stats Tracker",
    description="API for basketball statistics and analytics",
    version=VERSION_INFO["version"],
)

# Add middleware for proxy headers (Cloud Run)
app.add_middleware(ProxyHeadersMiddleware)

# Only add TrustedHostMiddleware in production
if os.getenv("APP_ENV") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.run.app", "*.googleusercontent.com", "league-stats.net", "*.league-stats.net"],
    )

# Setup static files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for container/load balancer probes."""
    return {"status": "ok", "version": VERSION_INFO["version"], "full_version": VERSION_INFO["full_version"]}

# Include routers
app.include_router(auth_router)  # Auth router first for authentication endpoints
app.include_router(pages_router)
app.include_router(games_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(admin_router)
app.include_router(reports_router)
