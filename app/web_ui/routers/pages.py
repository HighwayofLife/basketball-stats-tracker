"""HTML pages router for Basketball Stats Tracker."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.data_access import models
from app.data_access.db_session import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pages"])

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the dashboard home page."""
    try:
        with get_db_session() as session:
            # Get recent games for dashboard
            recent_games = session.query(models.Game).order_by(models.Game.date.desc()).limit(5).all()

            # Convert to dictionary for template, calculating scores from player stats
            recent_games_data = []
            for game in recent_games:
                # Get player stats for both teams
                playing_team_stats = (
                    session.query(models.PlayerGameStats)
                    .join(models.Player)
                    .filter(
                        models.PlayerGameStats.game_id == game.id,
                        models.Player.team_id == game.playing_team_id,
                    )
                    .all()
                )

                opponent_team_stats = (
                    session.query(models.PlayerGameStats)
                    .join(models.Player)
                    .filter(
                        models.PlayerGameStats.game_id == game.id,
                        models.Player.team_id == game.opponent_team_id,
                    )
                    .all()
                )

                # Calculate team scores from player stats
                home_score = sum(s.total_ftm + s.total_2pm * 2 + s.total_3pm * 3 for s in playing_team_stats)
                away_score = sum(s.total_ftm + s.total_2pm * 2 + s.total_3pm * 3 for s in opponent_team_stats)

                recent_games_data.append({
                    "id": game.id,
                    "date": game.date,
                    "home_team": game.playing_team.display_name or game.playing_team.name,
                    "away_team": game.opponent_team.display_name or game.opponent_team.name,
                    "home_score": home_score,
                    "away_score": away_score,
                })

            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "title": "Basketball Stats Dashboard",
                    "recent_games": recent_games_data,
                },
            )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/games", response_class=HTMLResponse)
async def games_page(request: Request):
    """Render the games list page."""
    return templates.TemplateResponse("games/index.html", {"request": request, "title": "Basketball Games"})


@router.get("/games/create", response_class=HTMLResponse)
async def create_game_page(request: Request):
    """Render the create game page."""
    return templates.TemplateResponse("games/create.html", {"request": request, "title": "Create New Game"})


@router.get("/teams", response_class=HTMLResponse)
async def teams_page(request: Request):
    """Render the teams management page."""
    return templates.TemplateResponse("teams/index.html", {"request": request, "title": "Team Management"})


@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_detail_page(request: Request, team_id: int):
    """Render the team detail page."""
    return templates.TemplateResponse("teams/detail.html", {"request": request, "title": "Team Details"})


@router.get("/players", response_class=HTMLResponse)
async def players_page(request: Request):
    """Render the players management page."""
    return templates.TemplateResponse("players/index.html", {"request": request, "title": "Player Management"})


@router.get("/games/{game_id}", response_class=HTMLResponse)
async def game_detail_page(request: Request, game_id: int):
    """Render the game detail page with box score."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            return templates.TemplateResponse(
                "games/detail.html",
                {
                    "request": request,
                    "title": f"{game.opponent_team.display_name or game.opponent_team.name} @ {game.playing_team.display_name or game.playing_team.name}",
                    "game_id": game_id,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering game detail page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/games/{game_id}/edit-stats", response_class=HTMLResponse)
async def game_edit_stats_page(request: Request, game_id: int):
    """Render the game stats editing page."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            # Get player stats for both teams
            playing_team_stats = (
                session.query(models.PlayerGameStats)
                .join(models.Player)
                .filter(
                    models.PlayerGameStats.game_id == game_id,
                    models.Player.team_id == game.playing_team_id,
                )
                .order_by(models.Player.jersey_number)
                .all()
            )

            opponent_team_stats = (
                session.query(models.PlayerGameStats)
                .join(models.Player)
                .filter(
                    models.PlayerGameStats.game_id == game_id,
                    models.Player.team_id == game.opponent_team_id,
                )
                .order_by(models.Player.jersey_number)
                .all()
            )

            # Calculate team scores
            home_score = sum(s.total_ftm + s.total_2pm * 2 + s.total_3pm * 3 for s in playing_team_stats)
            away_score = sum(s.total_ftm + s.total_2pm * 2 + s.total_3pm * 3 for s in opponent_team_stats)

            return templates.TemplateResponse(
                "games/edit_stats.html",
                {
                    "request": request,
                    "title": f"Edit Stats - {game.opponent_team.name} @ {game.playing_team.name}",
                    "game": game,
                    "playing_team_stats": playing_team_stats,
                    "opponent_team_stats": opponent_team_stats,
                    "home_score": home_score,
                    "away_score": away_score,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering game edit stats page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/games/{game_id}/live", response_class=HTMLResponse)
async def game_live_entry_page(request: Request, game_id: int):
    """Render the live game entry page."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            return templates.TemplateResponse(
                "games/live_entry.html",
                {
                    "request": request,
                    "title": f"Live Entry: {game.opponent_team.name} @ {game.playing_team.name}",
                    "game_id": game_id,
                    "home_team": game.playing_team.name,
                    "away_team": game.opponent_team.name,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering live entry page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/data-corrections", response_class=HTMLResponse)
async def admin_data_corrections_page(request: Request):
    """Render the data corrections admin page."""
    return templates.TemplateResponse(
        "admin/data_corrections.html", {"request": request, "title": "Data Corrections Admin"}
    )


@router.get("/players/{player_id}", response_class=HTMLResponse)
async def player_detail_page(request: Request, player_id: int):
    """Render the player detail page."""
    try:
        with get_db_session() as session:
            player = session.query(models.Player).filter(models.Player.id == player_id).first()
            
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")
            
            return templates.TemplateResponse(
                "players/detail.html",
                {
                    "request": request,
                    "title": f"{player.name} - Player Profile",
                    "player_id": player_id,
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering player detail page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/scorebook", response_class=HTMLResponse)
async def scorebook_entry_page(request: Request):
    """Render the scorebook entry page."""
    return templates.TemplateResponse("games/scorebook_entry.html", {"request": request, "title": "Scorebook Entry"})
