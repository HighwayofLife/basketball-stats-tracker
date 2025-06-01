# pylint: disable=singleton-comparison
"""FastAPI application for Basketball Stats Tracker."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.auth.jwt_handler import verify_token
from app.auth.models import UserRole
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


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce authentication and authorization based on HTTP methods and paths."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for certain paths
        if request.url.path in [
            "/health",
            "/",
            "/login",
            "/auth/login",
            "/auth/token",
            "/auth/callback",
            "/static",
        ] or request.url.path.startswith("/static/"):
            return await call_next(request)

        # Check if authentication is required
        requires_auth = False
        required_role = None

        # Admin routes require admin role
        if request.url.path.startswith("/admin/"):
            requires_auth = True
            required_role = UserRole.ADMIN

        # PUT/DELETE operations require at least user role
        elif (
            request.method in ["PUT", "DELETE"]
            or request.method == "POST"
            and not request.url.path.startswith("/auth/")
        ):
            requires_auth = True
            required_role = UserRole.USER

        if requires_auth:
            # Extract token from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Not authenticated"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            token = auth_header.split(" ")[1]

            # Verify token
            payload = verify_token(token)
            if payload is None:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authentication credentials"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Get user role from token
            user_id = payload.get("sub")
            if user_id is None:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid token"},
                )

            # Check role
            user_role_str = payload.get("role")
            if not user_role_str:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "No role assigned"},
                )

            # Convert string role to enum
            try:
                user_role = UserRole(user_role_str)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Invalid role"},
                )

            # Check role hierarchy
            if required_role == UserRole.ADMIN and user_role != UserRole.ADMIN:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Admin access required"},
                )
            elif required_role == UserRole.USER and user_role not in [UserRole.USER, UserRole.ADMIN]:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "User access required"},
                )

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

# Add middleware for authentication and authorization
# Commented out - using dependency injection instead for better testability
# app.add_middleware(AuthorizationMiddleware)

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
