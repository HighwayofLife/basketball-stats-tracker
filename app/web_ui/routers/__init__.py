"""Web UI routers package."""

from .admin import router as admin_router
from .games import router as games_router
from .pages import router as pages_router
from .players import router as players_router
from .reports import router as reports_router
from .teams import router as teams_router

__all__ = ["admin_router", "games_router", "pages_router", "players_router", "teams_router", "reports_router"]
