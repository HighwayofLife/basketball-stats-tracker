"""FastAPI application for Basketball Stats Tracker."""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.data_access import models
from app.data_access.db_session import get_db_session
from app.reports import ReportGenerator
from app.utils import stats_calculator

from .schemas import BoxScoreResponse, GameSummary, PlayerStats, TeamStats

# Configure logger
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Basketball Stats Tracker",
    description="API for basketball statistics and analytics",
    version="0.1.0",
)

# Setup templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the dashboard home page."""
    try:
        with get_db_session() as session:
            # Get recent games for dashboard
            recent_games = session.query(models.Game).order_by(models.Game.date.desc()).limit(5).all()

            # Convert to dictionary for template
            recent_games_data = [
                {
                    "id": game.id,
                    "date": game.date,
                    "home_team": game.playing_team.name,
                    "away_team": game.opponent_team.name,
                    "home_score": 0,  # To be calculated from player stats
                    "away_score": 0,  # To be calculated from player stats
                }
                for game in recent_games
            ]

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


@app.get("/v1/games", response_model=list[GameSummary])
async def list_games(limit: int = 20, offset: int = 0, team_id: int | None = None):
    """
    Get a list of games with optional filtering.

    Args:
        limit: Maximum number of games to return
        offset: Number of games to skip
        team_id: Optional filter for a specific team
    """
    try:
        with get_db_session() as session:
            query = session.query(models.Game)

            # Apply team filter if provided
            if team_id is not None:
                query = query.filter(
                    (models.Game.playing_team_id == team_id) | (models.Game.opponent_team_id == team_id)
                )

            # Apply pagination and ordering
            games = query.order_by(models.Game.date.desc()).offset(offset).limit(limit).all()

            result = []
            for game in games:
                # Calculate scores from player stats
                playing_team_score = 0
                opponent_team_score = 0

                # In a real implementation, you would calculate this from the player stats
                # For now, we'll just use placeholder values

                result.append(
                    GameSummary(
                        id=game.id,
                        date=game.date.isoformat() if game.date else "",
                        home_team=game.playing_team.name,
                        home_team_id=game.playing_team_id,
                        away_team=game.opponent_team.name,
                        away_team_id=game.opponent_team_id,
                        home_score=playing_team_score,
                        away_score=opponent_team_score,
                    )
                )

            return result
    except Exception as e:
        logger.error(f"Error retrieving games: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve games") from e


@app.get("/v1/games/{game_id}", response_model=GameSummary)
async def get_game(game_id: int):
    """Get basic information about a specific game."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            # Calculate scores from player stats
            playing_team_score = 0
            opponent_team_score = 0

            # In a real implementation, you would calculate this from the player stats
            # For now, we'll just use placeholder values

            return GameSummary(
                id=game.id,
                date=game.date.isoformat() if game.date else "",
                home_team=game.playing_team.name,
                home_team_id=game.playing_team_id,
                away_team=game.opponent_team.name,
                away_team_id=game.opponent_team_id,
                home_score=playing_team_score,
                away_score=opponent_team_score,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve game") from e


@app.get("/v1/games/{game_id}/box-score", response_model=BoxScoreResponse)
async def get_box_score(game_id: int):
    """Get detailed box score for a specific game."""
    try:
        with get_db_session() as session:
            # Use existing ReportGenerator to generate box score
            report_gen = ReportGenerator(session, stats_calculator)
            player_stats, game_summary = report_gen.get_game_box_score_data(game_id)

            if not player_stats or not game_summary:
                raise HTTPException(status_code=404, detail="Game not found")

            # Map the field names from the report generator to what our API expects
            playing_team_id = None
            opponent_team_id = None

            # Get the actual team IDs from the game
            game = session.query(models.Game).filter(models.Game.id == game_id).first()
            if game:
                playing_team_id = game.playing_team_id
                opponent_team_id = game.opponent_team_id

            # Filter players by team
            playing_team_players = [p for p in player_stats if p.get("team_id") == playing_team_id]
            opponent_team_players = [p for p in player_stats if p.get("team_id") == opponent_team_id]

            # Convert player stats to the expected format
            playing_team_player_stats = [
                PlayerStats(
                    player_id=p.get("player_id"),
                    name=p.get("player_name"),
                    stats={k: v for k, v in p.items() if k not in ["player_id", "player_name", "team_id", "team_name"]},
                )
                for p in playing_team_players
            ]

            opponent_team_player_stats = [
                PlayerStats(
                    player_id=p.get("player_id"),
                    name=p.get("player_name"),
                    stats={k: v for k, v in p.items() if k not in ["player_id", "player_name", "team_id", "team_name"]},
                )
                for p in opponent_team_players
            ]

            # Calculate scores
            playing_team_score = sum(p.get("points", 0) for p in playing_team_players)
            opponent_team_score = sum(p.get("points", 0) for p in opponent_team_players)

            # Create the response
            return BoxScoreResponse(
                game_id=game_id,
                game_date=str(game.date) if game and game.date else "",
                home_team=TeamStats(
                    team_id=playing_team_id or 0,  # Provide default value of 0 when None
                    name=game_summary.get("playing_team", ""),
                    score=playing_team_score,
                    stats={},  # Team stats aggregation would go here
                    players=playing_team_player_stats,
                ),
                away_team=TeamStats(
                    team_id=opponent_team_id or 0,  # Provide default value of 0 when None
                    name=game_summary.get("opponent_team", ""),
                    score=opponent_team_score,
                    stats={},  # Team stats aggregation would go here
                    players=opponent_team_player_stats,
                ),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating box score for game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate box score") from e


@app.get("/v1/teams", response_model=list[dict[str, Any]])
async def list_teams():
    """Get a list of all teams."""
    try:
        with get_db_session() as session:
            teams = session.query(models.Team).all()

            return [
                {
                    "id": team.id,
                    "name": team.name,
                    # "abbreviation": team.abbreviation,  # This field doesn't exist in the model
                }
                for team in teams
            ]
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve teams") from e


@app.get("/v1/teams/{team_id}", response_model=dict[str, Any])
async def get_team(team_id: int):
    """Get detailed information about a specific team."""
    try:
        with get_db_session() as session:
            team = session.query(models.Team).filter(models.Team.id == team_id).first()

            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            # Get team roster
            players = session.query(models.Player).filter(models.Player.team_id == team_id).all()

            return {
                "id": team.id,
                "name": team.name,
                # "abbreviation": team.abbreviation,  # This field doesn't exist in the model
                "roster": [
                    {
                        "id": player.id,
                        "name": player.name,
                        "jersey_number": player.jersey_number,
                        # "position": player.position,  # This field doesn't exist in the model
                    }
                    for player in players
                ],
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team") from e


@app.get("/games", response_class=HTMLResponse)
async def games_page(request: Request):
    """Render the games list page."""
    return templates.TemplateResponse("games/index.html", {"request": request, "title": "Basketball Games"})


@app.get("/games/{game_id}", response_class=HTMLResponse)
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
                    "title": f"{game.opponent_team.name} @ {game.playing_team.name}",
                    "game_id": game_id,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering game detail page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
