"""Matchup preview router for scheduled games."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.data_access.db_session import get_db_session
from app.services.matchup_service import MatchupService
from app.web_ui.dependencies import get_template_auth_context
from app.web_ui.templates_config import templates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduled-games", tags=["matchup"])


@router.get("/{scheduled_game_id}/matchup", response_class=HTMLResponse)
async def view_matchup(
    request: Request,
    scheduled_game_id: int,
    auth_context: dict = Depends(get_template_auth_context),
):
    """
    Display matchup preview for a scheduled game.

    Args:
        request: FastAPI request object
        scheduled_game_id: The ID of the scheduled game

    Returns:
        HTML response with the matchup preview page
    """
    try:
        with get_db_session() as session:
            matchup_service = MatchupService(session)
            matchup_data = matchup_service.get_formatted_matchup_data(scheduled_game_id)

            if not matchup_data:
                raise HTTPException(status_code=404, detail="Scheduled game not found")

            # Create context with formatted data and authentication context
            context = {
                **auth_context,  # Include authentication context
                **matchup_data,  # Include all formatted matchup data
            }

            return templates.TemplateResponse("matchup.html", context)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing matchup for scheduled game {scheduled_game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load matchup preview") from e


@router.get("/{scheduled_game_id}/edit", response_class=HTMLResponse)
async def edit_scheduled_game(
    request: Request,
    scheduled_game_id: int,
    auth_context: dict = Depends(get_template_auth_context),
):
    """
    Display edit form for a scheduled game.

    Args:
        request: FastAPI request object
        scheduled_game_id: The ID of the scheduled game

    Returns:
        HTML response with the edit game page
    """
    try:
        with get_db_session() as session:
            # Import ScheduledGame model
            from app.data_access.models import ScheduledGame

            # Get the scheduled game
            scheduled_game = session.query(ScheduledGame).filter(ScheduledGame.id == scheduled_game_id).first()

            if not scheduled_game:
                raise HTTPException(status_code=404, detail="Scheduled game not found")

            # Create context with scheduled game data
            context = {
                **auth_context,
                "title": "Edit Scheduled Game",
                "scheduled_game": scheduled_game,
                "game_date": scheduled_game.scheduled_date.strftime("%Y-%m-%d")
                if scheduled_game.scheduled_date
                else "",
                "game_time": scheduled_game.scheduled_time.strftime("%H:%M") if scheduled_game.scheduled_time else "",
                "is_edit": True,  # Flag to indicate this is an edit operation
            }

            return templates.TemplateResponse("games/create.html", context)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing scheduled game {scheduled_game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load edit form") from e
