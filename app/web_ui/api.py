# pylint: disable=singleton-comparison
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
from app.services.game_state_service import GameStateService
from app.utils import stats_calculator

from .schemas import (
    ActivePlayer,
    BoxScoreResponse,
    GameCreateRequest,
    GameEventInfo,
    GameEventResponse,
    GameStartRequest,
    GameStateInfo,
    GameStateResponse,
    GameSummary,
    PlayerCreateRequest,
    PlayerResponse,
    PlayerStats,
    PlayerUpdateRequest,
    RecordFoulRequest,
    RecordShotRequest,
    SubstitutionRequest,
    TeamCreateRequest,
    TeamDetailResponse,
    TeamResponse,
    TeamStats,
    TeamUpdateRequest,
)

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


@app.get("/games/create", response_class=HTMLResponse)
async def create_game_page(request: Request):
    """Render the create game page."""
    return templates.TemplateResponse("games/create.html", {"request": request, "title": "Create New Game"})


@app.get("/teams", response_class=HTMLResponse)
async def teams_page(request: Request):
    """Render the teams management page."""
    return templates.TemplateResponse("teams/index.html", {"request": request, "title": "Team Management"})


@app.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_detail_page(request: Request, team_id: int):
    """Render the team detail page."""
    return templates.TemplateResponse("teams/detail.html", {"request": request, "title": "Team Details"})


@app.get("/players", response_class=HTMLResponse)
async def players_page(request: Request):
    """Render the players management page."""
    return templates.TemplateResponse("players/index.html", {"request": request, "title": "Player Management"})


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


@app.get("/games/{game_id}/live", response_class=HTMLResponse)
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


# Live Game Entry API Endpoints


@app.post("/v1/games", response_model=GameSummary)
async def create_game(game_data: GameCreateRequest):
    """Create a new game."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            game = game_service.create_game(
                date=game_data.date,
                home_team_id=game_data.home_team_id,
                away_team_id=game_data.away_team_id,
                location=game_data.location,
                scheduled_time=game_data.scheduled_time,
                notes=game_data.notes,
            )

            return GameSummary(
                id=game.id,
                date=game.date.isoformat(),
                home_team=game.playing_team.name,
                home_team_id=game.playing_team_id,
                away_team=game.opponent_team.name,
                away_team_id=game.opponent_team_id,
                home_score=0,
                away_score=0,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error creating game: {e}")
        raise HTTPException(status_code=500, detail="Failed to create game") from e


@app.post("/v1/games/{game_id}/start")
async def start_game(game_id: int, start_data: GameStartRequest):
    """Start a game with starting lineups."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            game_state = game_service.start_game(
                game_id=game_id,
                home_starters=start_data.home_starters,
                away_starters=start_data.away_starters,
            )

            return {
                "game_id": game_id,
                "state": "live",
                "current_quarter": game_state.current_quarter,
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error starting game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start game") from e


@app.post("/v1/games/{game_id}/events/shot", response_model=GameEventResponse)
async def record_shot(game_id: int, shot_data: RecordShotRequest):
    """Record a shot attempt."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            result = game_service.record_shot(
                game_id=game_id,
                player_id=shot_data.player_id,
                shot_type=shot_data.shot_type,
                made=shot_data.made,
                quarter=shot_data.quarter,
                assisted_by=shot_data.assisted_by,
            )

            return GameEventResponse(
                event_id=result["event_id"],
                player_id=result["player_id"],
                event_type="shot",
                quarter=result["quarter"],
                details={
                    "shot_type": result["shot_type"],
                    "made": result["made"],
                },
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error recording shot: {e}")
        raise HTTPException(status_code=500, detail="Failed to record shot") from e


@app.post("/v1/games/{game_id}/events/foul", response_model=GameEventResponse)
async def record_foul(game_id: int, foul_data: RecordFoulRequest):
    """Record a foul."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            result = game_service.record_foul(
                game_id=game_id,
                player_id=foul_data.player_id,
                foul_type=foul_data.foul_type,
                quarter=foul_data.quarter,
            )

            return GameEventResponse(
                event_id=result["event_id"],
                player_id=result["player_id"],
                event_type="foul",
                quarter=result["quarter"],
                details={
                    "foul_type": result["foul_type"],
                    "total_fouls": result["total_fouls"],
                },
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error recording foul: {e}")
        raise HTTPException(status_code=500, detail="Failed to record foul") from e


@app.post("/v1/games/{game_id}/players/substitute")
async def substitute_players(game_id: int, sub_data: SubstitutionRequest):
    """Substitute players during a game."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            result = game_service.substitute_players(
                game_id=game_id,
                team_id=sub_data.team_id,
                players_out=sub_data.players_out,
                players_in=sub_data.players_in,
            )

            return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error substituting players: {e}")
        raise HTTPException(status_code=500, detail="Failed to substitute players") from e


@app.post("/v1/games/{game_id}/end-quarter")
async def end_quarter(game_id: int):
    """End the current quarter."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            game_state = game_service.end_quarter(game_id)

            return {
                "game_id": game_id,
                "current_quarter": game_state.current_quarter,
                "is_live": game_state.is_live,
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error ending quarter: {e}")
        raise HTTPException(status_code=500, detail="Failed to end quarter") from e


@app.post("/v1/games/{game_id}/finalize")
async def finalize_game(game_id: int):
    """Finalize a game."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            result = game_service.finalize_game(game_id)

            return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error finalizing game: {e}")
        raise HTTPException(status_code=500, detail="Failed to finalize game") from e


@app.get("/v1/games/{game_id}/live", response_model=GameStateResponse)
async def get_live_game_state(game_id: int):
    """Get the current state of a live game."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            state_data = game_service.get_live_game_state(game_id)

            return GameStateResponse(
                game_state=GameStateInfo(**state_data["game_state"]),
                active_players={
                    team: [ActivePlayer(**player) for player in players]
                    for team, players in state_data["active_players"].items()
                },
                recent_events=[GameEventInfo(**event) for event in state_data["recent_events"]],
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error getting live game state: {e}")
        raise HTTPException(status_code=500, detail="Failed to get game state") from e


@app.delete("/v1/games/{game_id}/events/last")
async def undo_last_event(game_id: int):
    """Undo the last event in a game."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)
            result = game_service.undo_last_event(game_id)

            return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error undoing event: {e}")
        raise HTTPException(status_code=500, detail="Failed to undo event") from e


# Team Management API Endpoints


@app.get("/v1/teams/detail", response_model=list[TeamResponse])
async def list_teams_with_counts():
    """Get a list of all teams with player counts."""
    try:
        with get_db_session() as session:
            teams = session.query(models.Team).all()

            result = []
            for team in teams:
                player_count = (
                    session.query(models.Player)
                    .filter(models.Player.team_id == team.id, models.Player.is_active == True)
                    .count()
                )

                result.append(TeamResponse(id=team.id, name=team.name, player_count=player_count))

            return result
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve teams") from e


@app.post("/v1/teams/new", response_model=TeamResponse)
async def create_team(team_data: TeamCreateRequest):
    """Create a new team."""
    try:
        with get_db_session() as session:
            # Check if team name already exists
            existing_team = session.query(models.Team).filter(models.Team.name == team_data.name).first()
            if existing_team:
                raise HTTPException(status_code=400, detail="Team name already exists")

            team = models.Team(name=team_data.name)
            session.add(team)
            session.commit()

            return TeamResponse(id=team.id, name=team.name, player_count=0)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        raise HTTPException(status_code=500, detail="Failed to create team") from e


@app.get("/v1/teams/{team_id}/detail", response_model=TeamDetailResponse)
async def get_team_detail(team_id: int):
    """Get detailed information about a specific team including players."""
    try:
        with get_db_session() as session:
            team = session.query(models.Team).filter(models.Team.id == team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            players = (
                session.query(models.Player)
                .filter(models.Player.team_id == team_id, models.Player.is_active == True)
                .order_by(models.Player.jersey_number)
                .all()
            )

            player_responses = [
                PlayerResponse(
                    id=player.id,
                    name=player.name,
                    team_id=player.team_id,
                    team_name=team.name,
                    jersey_number=player.jersey_number,
                    position=player.position,
                    height=player.height,
                    weight=player.weight,
                    year=player.year,
                    is_active=player.is_active,
                )
                for player in players
            ]

            return TeamDetailResponse(id=team.id, name=team.name, players=player_responses)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team") from e


@app.put("/v1/teams/{team_id}", response_model=TeamResponse)
async def update_team(team_id: int, team_data: TeamUpdateRequest):
    """Update a team."""
    try:
        with get_db_session() as session:
            team = session.query(models.Team).filter(models.Team.id == team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            # Check if new name conflicts with existing team
            if team_data.name != team.name:
                existing_team = (
                    session.query(models.Team)
                    .filter(models.Team.name == team_data.name, models.Team.id != team_id)
                    .first()
                )
                if existing_team:
                    raise HTTPException(status_code=400, detail="Team name already exists")

            team.name = team_data.name
            session.commit()

            player_count = (
                session.query(models.Player)
                .filter(models.Player.team_id == team.id, models.Player.is_active == True)
                .count()
            )

            return TeamResponse(id=team.id, name=team.name, player_count=player_count)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update team") from e


@app.delete("/v1/teams/{team_id}")
async def delete_team(team_id: int):
    """Delete a team and all its players."""
    try:
        with get_db_session() as session:
            team = session.query(models.Team).filter(models.Team.id == team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            # Check if team has games
            games_count = (
                session.query(models.Game)
                .filter((models.Game.playing_team_id == team_id) | (models.Game.opponent_team_id == team_id))
                .count()
            )

            if games_count > 0:
                raise HTTPException(
                    status_code=400, detail="Cannot delete team with existing games. Archive the team instead."
                )

            session.delete(team)
            session.commit()

            return {"message": "Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete team") from e


# Player Management API Endpoints


@app.get("/v1/players/list", response_model=list[PlayerResponse])
async def list_players(team_id: int | None = None, active_only: bool = True):
    """Get a list of players with optional team filtering."""
    try:
        with get_db_session() as session:
            query = session.query(models.Player, models.Team).join(models.Team, models.Player.team_id == models.Team.id)

            if team_id:
                query = query.filter(models.Player.team_id == team_id)

            if active_only:
                query = query.filter(models.Player.is_active == True)

            players_teams = query.order_by(models.Team.name, models.Player.jersey_number).all()

            result = [
                PlayerResponse(
                    id=player.id,
                    name=player.name,
                    team_id=player.team_id,
                    team_name=team.name,
                    jersey_number=player.jersey_number,
                    position=player.position,
                    height=player.height,
                    weight=player.weight,
                    year=player.year,
                    is_active=player.is_active,
                )
                for player, team in players_teams
            ]

            return result
    except Exception as e:
        logger.error(f"Error retrieving players: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve players") from e


@app.post("/v1/players/new", response_model=PlayerResponse)
async def create_player(player_data: PlayerCreateRequest):
    """Create a new player."""
    try:
        with get_db_session() as session:
            # Verify team exists
            team = session.query(models.Team).filter(models.Team.id == player_data.team_id).first()
            if not team:
                raise HTTPException(status_code=400, detail="Team not found")

            # Check for duplicate jersey number on same team
            existing_player = (
                session.query(models.Player)
                .filter(
                    models.Player.team_id == player_data.team_id,
                    models.Player.jersey_number == player_data.jersey_number,
                    models.Player.is_active == True,
                )
                .first()
            )
            if existing_player:
                raise HTTPException(
                    status_code=400, detail=f"Jersey number {player_data.jersey_number} already exists on this team"
                )

            player = models.Player(
                name=player_data.name,
                team_id=player_data.team_id,
                jersey_number=player_data.jersey_number,
                position=player_data.position,
                height=player_data.height,
                weight=player_data.weight,
                year=player_data.year,
                is_active=True,
            )
            session.add(player)
            session.commit()

            return PlayerResponse(
                id=player.id,
                name=player.name,
                team_id=player.team_id,
                team_name=team.name,
                jersey_number=player.jersey_number,
                position=player.position,
                height=player.height,
                weight=player.weight,
                year=player.year,
                is_active=player.is_active,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating player: {e}")
        raise HTTPException(status_code=500, detail="Failed to create player") from e


@app.get("/v1/players/{player_id}", response_model=PlayerResponse)
async def get_player(player_id: int):
    """Get detailed information about a specific player."""
    try:
        with get_db_session() as session:
            player = session.query(models.Player).filter(models.Player.id == player_id).first()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")

            return PlayerResponse(
                id=player.id,
                name=player.name,
                team_id=player.team_id,
                team_name=player.team.name,
                jersey_number=player.jersey_number,
                position=player.position,
                height=player.height,
                weight=player.weight,
                year=player.year,
                is_active=player.is_active,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve player") from e


@app.put("/v1/players/{player_id}", response_model=PlayerResponse)
async def update_player(player_id: int, player_data: PlayerUpdateRequest):
    """Update a player."""
    try:
        with get_db_session() as session:
            player = session.query(models.Player).filter(models.Player.id == player_id).first()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")

            # Update fields if provided
            if player_data.name is not None:
                player.name = player_data.name
            if player_data.team_id is not None:
                # Verify new team exists
                team = session.query(models.Team).filter(models.Team.id == player_data.team_id).first()
                if not team:
                    raise HTTPException(status_code=400, detail="Team not found")
                player.team_id = player_data.team_id
            if player_data.jersey_number is not None:
                # Check for duplicate jersey number on team
                team_id = player_data.team_id or player.team_id
                existing_player = (
                    session.query(models.Player)
                    .filter(
                        models.Player.team_id == team_id,
                        models.Player.jersey_number == player_data.jersey_number,
                        models.Player.id != player_id,
                        models.Player.is_active == True,
                    )
                    .first()
                )
                if existing_player:
                    raise HTTPException(
                        status_code=400, detail=f"Jersey number {player_data.jersey_number} already exists on this team"
                    )
                player.jersey_number = player_data.jersey_number
            if player_data.position is not None:
                player.position = player_data.position
            if player_data.height is not None:
                player.height = player_data.height
            if player_data.weight is not None:
                player.weight = player_data.weight
            if player_data.year is not None:
                player.year = player_data.year
            if player_data.is_active is not None:
                player.is_active = player_data.is_active

            session.commit()

            return PlayerResponse(
                id=player.id,
                name=player.name,
                team_id=player.team_id,
                team_name=player.team.name,
                jersey_number=player.jersey_number,
                position=player.position,
                height=player.height,
                weight=player.weight,
                year=player.year,
                is_active=player.is_active,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update player") from e


@app.delete("/v1/players/{player_id}")
async def delete_player(player_id: int):
    """Delete a player (actually deactivates them if they have game stats)."""
    try:
        with get_db_session() as session:
            player = session.query(models.Player).filter(models.Player.id == player_id).first()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")

            # Check if player has game stats
            stats_count = (
                session.query(models.PlayerGameStats).filter(models.PlayerGameStats.player_id == player_id).count()
            )

            if stats_count > 0:
                # Deactivate instead of delete to preserve data integrity
                player.is_active = False
                session.commit()
                return {"message": "Player deactivated successfully (has existing game stats)"}
            else:
                # Safe to delete if no game stats
                session.delete(player)
                session.commit()
                return {"message": "Player deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete player") from e
