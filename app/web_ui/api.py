# pylint: disable=singleton-comparison
"""FastAPI application for Basketball Stats Tracker."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import VERSION_INFO, settings

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

# Create FastAPI application
app = FastAPI(
    title="Basketball Stats Tracker",
    description="API for basketball statistics and analytics",
    version=VERSION_INFO["version"],
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY or "dev-session-key")

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
    version = VERSION_INFO.get("version", "unknown") if VERSION_INFO else "unknown"
    full_version = VERSION_INFO.get("full_version", "unknown") if VERSION_INFO else "unknown"
    return {"status": "ok", "version": version, "full_version": full_version}


# Include routers
app.include_router(auth_router)  # Auth router first for authentication endpoints
app.include_router(pages_router)
app.include_router(games_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(admin_router)
app.include_router(reports_router)
