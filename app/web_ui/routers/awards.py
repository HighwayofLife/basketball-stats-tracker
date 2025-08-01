"""Awards router for Basketball Stats Tracker."""

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config_data.awards import SEASON_AWARDS, WEEKLY_AWARDS, get_award_display_data
from app.data_access.models import Player, PlayerAward, Team
from app.dependencies import get_db
from app.web_ui.dependencies import get_template_auth_context
from app.web_ui.templates_config import templates

logger = logging.getLogger(__name__)
router = APIRouter(tags=["awards"])


@router.get("/awards", response_class=HTMLResponse)
async def awards_page(
    request: Request,
    session: Session = Depends(get_db),
    auth_context: dict = Depends(get_template_auth_context),
):
    """Render the awards showcase page."""
    context = {
        "request": request,
        "title": "Awards Showcase",
        **auth_context,
    }
    return templates.TemplateResponse("awards/index.html", context)


@router.get("/v1/awards")
async def get_awards(
    season: str = Query(None, description="Filter by specific season (e.g., '2024'), or 'all' for all seasons"),
    session: Session = Depends(get_db),
):
    """
    Get all awards data for display in the awards showcase.

    Returns awards grouped by season and type with complete display information.
    """
    try:
        # Base query with joins
        query = (
            session.query(PlayerAward)
            .join(Player, PlayerAward.player_id == Player.id)
            .join(Team, Player.team_id == Team.id)
            .options(joinedload(PlayerAward.player).joinedload(Player.team))
        )

        # Apply season filter if specified
        if season and season != "all":
            query = query.filter(PlayerAward.season == season)

        # Order by season desc, then by award type
        awards = query.order_by(
            PlayerAward.season.desc(), PlayerAward.award_type, PlayerAward.week_date.desc().nulls_last()
        ).all()

        # Get available seasons for filter dropdown
        seasons_query = session.query(PlayerAward.season).distinct().order_by(PlayerAward.season.desc())
        available_seasons = [s[0] for s in seasons_query.all()]

        # Group and format awards
        season_awards = {}
        weekly_awards = {}

        for award in awards:
            # Determine if this is a season or weekly award
            is_weekly = award.week_date is not None
            award_category = weekly_awards if is_weekly else season_awards

            # Create season group if it doesn't exist
            if award.season not in award_category:
                award_category[award.season] = {}

            # Create award type group if it doesn't exist
            if award.award_type not in award_category[award.season]:
                award_category[award.season][award.award_type] = []

            # Get award display data
            display_data = get_award_display_data(award.award_type, award.stat_value, award.points_scored)

            # Build complete award data
            award_data = {
                "player_id": award.player.id,
                "player_name": award.player.name,
                "team_name": award.player.team.name,
                "season": award.season,
                "week_date": award.week_date.isoformat() if award.week_date else None,
                "game_id": award.game_id,
                **display_data,
            }

            award_category[award.season][award.award_type].append(award_data)

        # Get award configuration for frontend
        award_configs = {"weekly": WEEKLY_AWARDS, "season": SEASON_AWARDS}

        return {
            "success": True,
            "season_awards": season_awards,
            "weekly_awards": weekly_awards,
            "available_seasons": available_seasons,
            "award_configs": award_configs,
            "total_awards": len(awards),
        }

    except Exception as e:
        logger.error(f"Error fetching awards data: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "season_awards": {},
            "weekly_awards": {},
            "available_seasons": [],
            "award_configs": {"weekly": {}, "season": {}},
            "total_awards": 0,
        }


@router.get("/v1/awards/{season}")
async def get_awards_by_season(
    season: str,
    session: Session = Depends(get_db),
):
    """Get awards data for a specific season."""
    return await get_awards(season=season, session=session)


@router.get("/v1/awards/stats/summary")
async def get_awards_summary(
    session: Session = Depends(get_db),
):
    """
    Get summary statistics about awards.

    Returns total counts by award type and season.
    """
    try:
        # Get total awards by type
        awards_by_type = (
            session.query(PlayerAward.award_type, func.count(PlayerAward.id).label("count"))
            .group_by(PlayerAward.award_type)
            .all()
        )

        # Get total awards by season
        awards_by_season = (
            session.query(PlayerAward.season, func.count(PlayerAward.id).label("count"))
            .group_by(PlayerAward.season)
            .order_by(PlayerAward.season.desc())
            .all()
        )

        # Get total unique players with awards
        unique_players = session.query(PlayerAward.player_id).distinct().count()

        return {
            "success": True,
            "awards_by_type": dict(awards_by_type),
            "awards_by_season": dict(awards_by_season),
            "total_awards": sum(count for _, count in awards_by_type),
            "unique_players_with_awards": unique_players,
        }

    except Exception as e:
        logger.error(f"Error fetching awards summary: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "awards_by_type": {},
            "awards_by_season": {},
            "total_awards": 0,
            "unique_players_with_awards": 0,
        }
