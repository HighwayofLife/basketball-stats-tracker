# app/web_ui/routers/awards_config.py

"""API router for award configuration endpoints."""

from fastapi import APIRouter

from app.config_data.awards import ALL_AWARDS, SEASON_AWARDS, WEEKLY_AWARDS

router = APIRouter(prefix="/api/awards", tags=["awards"])


@router.get("/config")
async def get_awards_config():
    """Get the complete award configuration for frontend use."""
    return {
        "weekly_awards": WEEKLY_AWARDS,
        "season_awards": SEASON_AWARDS,
        "all_awards": ALL_AWARDS,
    }


@router.get("/config/weekly")
async def get_weekly_awards_config():
    """Get weekly award configuration only."""
    return WEEKLY_AWARDS


@router.get("/config/season")
async def get_season_awards_config():
    """Get season award configuration only."""
    return SEASON_AWARDS
