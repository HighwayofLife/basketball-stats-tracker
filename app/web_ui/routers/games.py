"""Games router for Basketball Stats Tracker."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.data_access import models
from app.data_access.db_session import get_db_session
from app.reports import ReportGenerator
from app.services.game_state_service import GameStateService
from app.utils import stats_calculator

from ..schemas import (
    ActivePlayer,
    BoxScoreResponse,
    GameCreateRequest,
    GameEventInfo,
    GameEventResponse,
    GameStartRequest,
    GameStateInfo,
    GameStateResponse,
    GameSummary,
    PlayerStats,
    RecordFoulRequest,
    RecordShotRequest,
    SubstitutionRequest,
    TeamStats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/games", tags=["games"])


@router.get("", response_model=list[GameSummary])
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

            from app.services.score_calculation_service import ScoreCalculationService

            result = []
            for game in games:
                # Get all player stats for this game
                player_stats = (
                    session.query(models.PlayerGameStats).filter(models.PlayerGameStats.game_id == game.id).all()
                )

                # Calculate scores using the centralized service
                playing_team_score, opponent_team_score = ScoreCalculationService.calculate_game_scores(
                    game, player_stats
                )

                result.append(
                    GameSummary(
                        id=game.id,
                        date=game.date.isoformat() if game.date else "",
                        home_team=game.playing_team.display_name or game.playing_team.name,
                        home_team_id=game.playing_team_id,
                        away_team=game.opponent_team.display_name or game.opponent_team.name,
                        away_team_id=game.opponent_team_id,
                        home_score=playing_team_score,
                        away_score=opponent_team_score,
                    )
                )

            return result
    except Exception as e:
        logger.error(f"Error retrieving games: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve games") from e


@router.get("/{game_id}", response_model=GameSummary)
async def get_game(game_id: int):
    """Get basic information about a specific game."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter(models.Game.id == game_id).first()

            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            from app.services.score_calculation_service import ScoreCalculationService

            # Get all player stats for this game
            player_stats = session.query(models.PlayerGameStats).filter(models.PlayerGameStats.game_id == game.id).all()

            # Calculate scores using the centralized service
            playing_team_score, opponent_team_score = ScoreCalculationService.calculate_game_scores(game, player_stats)

            return GameSummary(
                id=game.id,
                date=game.date.isoformat() if game.date else "",
                home_team=game.playing_team.display_name or game.playing_team.name,
                home_team_id=game.playing_team_id,
                away_team=game.opponent_team.display_name or game.opponent_team.name,
                away_team_id=game.opponent_team_id,
                home_score=playing_team_score,
                away_score=opponent_team_score,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve game") from e


@router.get("/{game_id}/box-score", response_model=BoxScoreResponse)
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

            # Get team display names from the game
            playing_team_name = game.playing_team.display_name or game.playing_team.name if game else ""
            opponent_team_name = game.opponent_team.display_name or game.opponent_team.name if game else ""

            # Filter players by team name (report generator provides team name, not ID)
            playing_team_players = [p for p in player_stats if p.get("team") == playing_team_name]
            opponent_team_players = [p for p in player_stats if p.get("team") == opponent_team_name]

            # Convert player stats to the expected format
            playing_team_player_stats = [
                PlayerStats(
                    player_id=p.get("player_id", 0),
                    name=p.get("name", ""),
                    stats={k: v for k, v in p.items() if k not in ["player_id", "name", "team", "jersey"]},
                )
                for p in playing_team_players
            ]

            opponent_team_player_stats = [
                PlayerStats(
                    player_id=p.get("player_id", 0),
                    name=p.get("name", ""),
                    stats={k: v for k, v in p.items() if k not in ["player_id", "name", "team", "jersey"]},
                )
                for p in opponent_team_players
            ]

            # Calculate scores
            playing_team_score = sum(p.get("points", 0) for p in playing_team_players)
            opponent_team_score = sum(p.get("points", 0) for p in opponent_team_players)

            # Calculate quarter-by-quarter scores (separate from main score calculation)
            playing_team_quarters = {1: 0, 2: 0, 3: 0, 4: 0}
            opponent_team_quarters = {1: 0, 2: 0, 3: 0, 4: 0}

            # Get all player game stats for this game to access quarter stats
            all_player_game_stats = (
                session.query(models.PlayerGameStats).filter(models.PlayerGameStats.game_id == game_id).all()
            )

            logger.info(f"Found {len(all_player_game_stats)} player game stats for game {game_id}")

            for pgs in all_player_game_stats:
                # Get quarter stats for this player
                quarter_stats = (
                    session.query(models.PlayerQuarterStats)
                    .filter(models.PlayerQuarterStats.player_game_stat_id == pgs.id)
                    .all()
                )

                logger.info(f"Player {pgs.player.name} has {len(quarter_stats)} quarter stats")

                for qs in quarter_stats:
                    # Calculate points for this quarter
                    quarter_points = qs.ftm + (qs.fg2m * 2) + (qs.fg3m * 3)

                    # Add to appropriate team's quarter total
                    if pgs.player.team_id == playing_team_id:
                        playing_team_quarters[qs.quarter_number] += quarter_points
                        logger.info(f"Added {quarter_points} points to playing team Q{qs.quarter_number}")
                    elif pgs.player.team_id == opponent_team_id:
                        opponent_team_quarters[qs.quarter_number] += quarter_points
                        logger.info(f"Added {quarter_points} points to opponent team Q{qs.quarter_number}")

            logger.info(f"Playing team quarters: {playing_team_quarters}")
            logger.info(f"Opponent team quarters: {opponent_team_quarters}")

            # Find top player from each team
            def get_top_player(players):
                if not players:
                    return None
                # Sort by points (descending), then by FG% (descending)
                sorted_players = sorted(
                    players,
                    key=lambda p: (
                        p.get("points", 0),
                        # Calculate FG% - handle division by zero
                        (p.get("fg2m", 0) + p.get("fg3m", 0)) / max((p.get("fg2a", 0) + p.get("fg3a", 0)), 1) * 100,
                    ),
                    reverse=True,
                )
                if sorted_players:
                    top = sorted_players[0]
                    # Calculate FG percentage for the top player
                    fgm = top.get("fg2m", 0) + top.get("fg3m", 0)
                    fga = top.get("fg2a", 0) + top.get("fg3a", 0)
                    fg_percentage = (fgm / fga * 100) if fga > 0 else 0
                    return {
                        "player_id": top.get("player_id", 0),
                        "name": top.get("name", ""),
                        "jersey": top.get("jersey", ""),
                        "points": top.get("points", 0),
                        "fg_percentage": fg_percentage,
                        "rebounds": top.get("rebounds", 0),
                        "assists": top.get("assists", 0),
                        "fg2m": top.get("fg2m", 0),
                        "fg2a": top.get("fg2a", 0),
                        "fg3m": top.get("fg3m", 0),
                        "fg3a": top.get("fg3a", 0),
                    }
                return None

            home_top_player = get_top_player(playing_team_players)
            away_top_player = get_top_player(opponent_team_players)

            # Create the response
            return BoxScoreResponse(
                game_id=game_id,
                game_date=str(game.date) if game and game.date else "",
                home_team=TeamStats(
                    team_id=playing_team_id or 0,  # Provide default value of 0 when None
                    name=game_summary.get("playing_team", ""),
                    score=playing_team_score,
                    stats={"quarter_scores": playing_team_quarters},  # Add quarter scores to team stats
                    players=playing_team_player_stats,
                    top_player=home_top_player,
                ),
                away_team=TeamStats(
                    team_id=opponent_team_id or 0,  # Provide default value of 0 when None
                    name=game_summary.get("opponent_team", ""),
                    score=opponent_team_score,
                    stats={"quarter_scores": opponent_team_quarters},  # Add quarter scores to team stats
                    players=opponent_team_player_stats,
                    top_player=away_top_player,
                ),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating box score for game {game_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate box score") from e


@router.post("", response_model=GameSummary)
async def create_game(game_data: GameCreateRequest, current_user: User = Depends(get_current_user)):
    """Create a new game."""
    try:
        with get_db_session() as session:
            game_service = GameStateService(session)

            # Determine season if not provided
            season_id = game_data.season_id
            if season_id is None:
                from datetime import datetime

                from app.services.season_stats_service import SeasonStatsService

                game_date = datetime.strptime(game_data.date, "%Y-%m-%d").date()
                season_service = SeasonStatsService(session)
                season = season_service.get_or_create_season_from_date(game_date)
                season_id = season.id if season else None

            game = game_service.create_game(
                date=game_data.date,
                home_team_id=game_data.home_team_id,
                away_team_id=game_data.away_team_id,
                location=game_data.location,
                scheduled_time=game_data.scheduled_time,
                notes=game_data.notes,
                season_id=season_id,
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


@router.post("/{game_id}/start")
async def start_game(game_id: int, start_data: GameStartRequest, current_user: User = Depends(get_current_user)):
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


@router.post("/{game_id}/events/shot", response_model=GameEventResponse)
async def record_shot(game_id: int, shot_data: RecordShotRequest, current_user: User = Depends(get_current_user)):
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


@router.post("/{game_id}/events/foul", response_model=GameEventResponse)
async def record_foul(game_id: int, foul_data: RecordFoulRequest, current_user: User = Depends(get_current_user)):
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


@router.post("/{game_id}/players/substitute")
async def substitute_players(
    game_id: int, sub_data: SubstitutionRequest, current_user: User = Depends(get_current_user)
):
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


@router.post("/{game_id}/end-quarter")
async def end_quarter(game_id: int, current_user: User = Depends(get_current_user)):
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


@router.post("/{game_id}/finalize")
async def finalize_game(game_id: int, current_user: User = Depends(get_current_user)):
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


@router.get("/{game_id}/live", response_model=GameStateResponse)
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


@router.delete("/{game_id}/events/last")
async def undo_last_event(game_id: int, current_user: User = Depends(get_current_user)):
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


@router.put("/{game_id}/stats/batch-update")
async def batch_update_game_stats(game_id: int, updates: dict, current_user: User = Depends(get_current_user)):
    """Batch update player stats for a game with undo support."""
    try:
        with get_db_session() as session:
            from app.services.data_correction_service import DataCorrectionService

            correction_service = DataCorrectionService(session)

            # Parse updates: {stats_id: {field: value}}
            stats_updates = {}
            for stats_id_str, field_updates in updates.get("updates", {}).items():
                stats_id = int(stats_id_str)
                stats_updates[stats_id] = field_updates

            # Execute batch update
            updated_stats = []
            for stats_id, field_updates in stats_updates.items():
                result = correction_service.update_player_game_stats(stats_id, field_updates)
                updated_stats.append(result)

            return {"status": "success", "updated": len(updated_stats)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error batch updating stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to update stats") from e


@router.get("/deleted")
async def get_deleted_games():
    """Get all soft-deleted games."""
    try:
        with get_db_session() as session:
            deleted_games = (
                session.query(models.Game).filter(models.Game.is_deleted).order_by(models.Game.deleted_at.desc()).all()
            )

            return [
                {
                    "id": game.id,
                    "date": game.date.isoformat(),
                    "home_team": game.playing_team.name,
                    "away_team": game.opponent_team.name,
                    "deleted_at": game.deleted_at.isoformat() if game.deleted_at else None,
                }
                for game in deleted_games
            ]
    except Exception as e:
        logger.error(f"Error getting deleted games: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deleted games") from e


@router.post("/{game_id}/restore")
async def restore_game(game_id: int, current_user: User = Depends(require_admin)):
    """Restore a soft-deleted game."""
    try:
        with get_db_session() as session:
            game = session.query(models.Game).filter_by(id=game_id).first()
            if not game:
                raise HTTPException(status_code=404, detail="Game not found")

            if not game.is_deleted:
                raise HTTPException(status_code=400, detail="Game is not deleted")

            game.is_deleted = False
            game.deleted_at = None
            game.deleted_by = None

            # Log the restore
            from app.services.audit_log_service import AuditLogService

            audit_service = AuditLogService(session)
            audit_service.log_restore(
                entity_type="game",
                entity_id=game_id,
                restored_values={"is_deleted": False},
                description=f"Restored game {game_id}",
            )

            session.commit()
            return {"success": True, "message": "Game restored successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring game: {e}")
        raise HTTPException(status_code=500, detail="Failed to restore game") from e


@router.post("/scorebook")
async def create_game_from_scorebook(scorebook_data: dict, current_user: User = Depends(get_current_user)):
    """Create a game from scorebook data entry."""
    try:
        with get_db_session() as session:
            # Import here to avoid circular imports
            from app.utils.scorebook_parser import parse_scorebook_entry

            # Validate required fields
            required_fields = ["date", "home_team_id", "away_team_id", "player_stats"]
            for field in required_fields:
                if field not in scorebook_data:
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

            # Validate teams exist
            home_team = session.query(models.Team).filter(models.Team.id == scorebook_data["home_team_id"]).first()
            away_team = session.query(models.Team).filter(models.Team.id == scorebook_data["away_team_id"]).first()

            if not home_team:
                raise HTTPException(status_code=400, detail="Home team not found")
            if not away_team:
                raise HTTPException(status_code=400, detail="Away team not found")
            if home_team.id == away_team.id:
                raise HTTPException(status_code=400, detail="Home and away teams must be different")

            # Create the game
            game_service = GameStateService(session)

            # Determine season from game date
            from datetime import datetime

            from app.services.season_stats_service import SeasonStatsService

            game_date = datetime.strptime(scorebook_data["date"], "%Y-%m-%d").date()
            season_service = SeasonStatsService(session)
            season = season_service.get_or_create_season_from_date(game_date)

            game = game_service.create_game(
                date=scorebook_data["date"],
                home_team_id=scorebook_data["home_team_id"],
                away_team_id=scorebook_data["away_team_id"],
                location=scorebook_data.get("location"),
                notes=scorebook_data.get("notes"),
                season_id=season.id if season else None,
            )

            # Process player statistics
            home_score = 0
            away_score = 0

            for player_data in scorebook_data["player_stats"]:
                try:
                    # Parse the scorebook entry
                    parsed_data = parse_scorebook_entry(player_data)
                    player_id = parsed_data["player_id"]

                    # Verify player exists
                    player = session.query(models.Player).filter(models.Player.id == player_id).first()
                    if not player:
                        raise HTTPException(status_code=400, detail=f"Player {player_id} not found")

                    # Create player game stats
                    game_stats = models.PlayerGameStats(
                        game_id=game.id,
                        player_id=player_id,
                        total_2pm=parsed_data["total_stats"]["fg2m"],
                        total_2pa=parsed_data["total_stats"]["fg2a"],
                        total_3pm=parsed_data["total_stats"]["fg3m"],
                        total_3pa=parsed_data["total_stats"]["fg3a"],
                        total_ftm=parsed_data["total_stats"]["ftm"],
                        total_fta=parsed_data["total_stats"]["fta"],
                        fouls=parsed_data["fouls"],
                    )
                    session.add(game_stats)
                    session.flush()

                    # Create quarter stats
                    for quarter_data in parsed_data["quarter_stats"]:
                        quarter_stats = models.PlayerQuarterStats(
                            player_game_stat_id=game_stats.id,
                            quarter_number=quarter_data["quarter_number"],
                            fg2m=quarter_data["fg2m"],
                            fg2a=quarter_data["fg2a"],
                            fg3m=quarter_data["fg3m"],
                            fg3a=quarter_data["fg3a"],
                            ftm=quarter_data["ftm"],
                            fta=quarter_data["fta"],
                        )
                        session.add(quarter_stats)

                    # Calculate player score and add to team total
                    player_score = (
                        parsed_data["total_stats"]["ftm"]
                        + parsed_data["total_stats"]["fg2m"] * 2
                        + parsed_data["total_stats"]["fg3m"] * 3
                    )

                    if player.team_id == scorebook_data["home_team_id"]:
                        home_score += player_score
                    elif player.team_id == scorebook_data["away_team_id"]:
                        away_score += player_score

                except ValueError as ve:
                    raise HTTPException(status_code=400, detail=f"Invalid player data: {str(ve)}") from ve

            session.commit()

            return {
                "game_id": game.id,
                "message": "Game created successfully from scorebook",
                "home_team": home_team.name,
                "away_team": away_team.name,
                "home_score": home_score,
                "away_score": away_score,
                "date": game.date.isoformat(),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating game from scorebook: {e}", exc_info=True)

        # Translate technical errors to user-friendly messages
        error_message = "Failed to create game from scorebook"

        # Check for common database constraint violations
        error_str = str(e).lower()
        if "duplicate key" in error_str and "uq_game_date_teams" in error_str:
            error_message = (
                "A game between these teams on this date already exists. Please check the game date and teams."
            )
        elif "foreign key" in error_str:
            error_message = "Invalid team or player reference. Please verify all team and player selections."
        elif "unique constraint" in error_str:
            if "jersey" in error_str:
                error_message = "A player with this jersey number already exists on the team."
            else:
                error_message = "This game data conflicts with existing records. Please check for duplicates."
        elif "not null" in error_str:
            error_message = "Missing required information. Please ensure all required fields are filled."

        raise HTTPException(status_code=400, detail=error_message) from e
