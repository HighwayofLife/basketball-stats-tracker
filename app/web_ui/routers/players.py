"""Players router for Basketball Stats Tracker."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import Integer, func

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.data_access import models
from app.data_access.db_session import get_db_session
from app.services.player_stats_service import PlayerStatsService
from app.services.season_stats_service import SeasonStatsService
from app.services.awards_service_v2 import get_player_potw_summary
from app.utils import stats_calculator
from app.web_ui.cache import invalidate_cache_after
from app.web_ui.dependencies import get_db

from ..schemas import PlayerCreateRequest, PlayerResponse, PlayerUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/players", tags=["players"])


def _get_potw_summary(session, player_id: int) -> dict:
    """Get Player of the Week summary using the new PlayerAward table."""
    try:
        return get_player_potw_summary(session, player_id)
    except Exception as e:
        logger.error(f"Error getting POTW summary for player {player_id}: {e}")
        # Return fallback data structure
        return {
            "current_season_count": 0,
            "total_count": 0,
            "awards_by_season": {},
            "recent_awards": []
        }


@router.get("/list", response_model=list[PlayerResponse])
async def list_players(team_id: int | None = None, active_only: bool = True, player_type: str | None = None):
    """Get a list of players with optional team filtering."""
    try:
        with get_db_session() as session:
            query = session.query(models.Player, models.Team).join(models.Team, models.Player.team_id == models.Team.id)

            if team_id:
                query = query.filter(models.Player.team_id == team_id)

            if active_only:
                query = query.filter(models.Player.is_active)

            if player_type:
                if player_type == "substitute":
                    query = query.filter(models.Player.is_substitute)
                elif player_type == "regular":
                    query = query.filter(~models.Player.is_substitute)

            players_teams = query.order_by(models.Team.name, func.cast(models.Player.jersey_number, Integer)).all()

            result = [
                PlayerResponse(
                    id=player.id,
                    name=player.name,
                    team_id=player.team_id,
                    team_name=team.name,
                    jersey_number=str(player.jersey_number),
                    position=player.position,
                    height=player.height,
                    weight=player.weight,
                    year=player.year,
                    is_active=player.is_active,
                    is_substitute=player.is_substitute,
                    thumbnail_image=player.thumbnail_image,
                )
                for player, team in players_teams
            ]

            return result
    except Exception as e:
        logger.error(f"Error retrieving players: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve players") from e


@router.post("/new", response_model=PlayerResponse)
@invalidate_cache_after
async def create_player(player_data: PlayerCreateRequest, current_user: User = Depends(get_current_user)):
    """Create a new player."""
    try:
        with get_db_session() as session:
            # Verify team exists
            team = session.query(models.Team).filter(models.Team.id == player_data.team_id).first()
            if not team:
                raise HTTPException(status_code=400, detail="Team not found")

            # Check for duplicate jersey number on same team
            # Cast both sides to string for comparison to handle mixed int/string types in database
            from sqlalchemy import String, cast

            jersey_str = str(player_data.jersey_number)
            existing_player = (
                session.query(models.Player)
                .filter(
                    models.Player.team_id == player_data.team_id,
                    cast(models.Player.jersey_number, String) == jersey_str,
                    models.Player.is_active,
                )
                .first()
            )
            if existing_player:
                raise HTTPException(
                    status_code=400, detail=f"Jersey number {player_data.jersey_number} already exists on this team"
                )

            # Check for duplicate player name on same team
            existing_name = (
                session.query(models.Player)
                .filter(
                    models.Player.team_id == player_data.team_id,
                    models.Player.name == player_data.name,
                    models.Player.is_active,
                )
                .first()
            )
            if existing_name:
                raise HTTPException(
                    status_code=400, detail=f"Player with name '{player_data.name}' already exists on {team.name}"
                )

            player = models.Player(
                name=player_data.name,
                team_id=player_data.team_id,
                jersey_number=str(player_data.jersey_number),
                position=player_data.position,
                height=player_data.height,
                weight=player_data.weight,
                year=player_data.year,
                is_active=True,
                is_substitute=player_data.is_substitute,
            )
            session.add(player)
            session.commit()

            return PlayerResponse(
                id=player.id,
                name=player.name,
                team_id=player.team_id,
                team_name=team.name,
                jersey_number=str(player.jersey_number),
                position=player.position,
                height=player.height,
                weight=player.weight,
                year=player.year,
                is_active=player.is_active,
                is_substitute=player.is_substitute,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating player {player_data.name}: {e}", exc_info=True)

        # Translate technical errors to user-friendly messages
        error_message = f"Failed to create player {player_data.name}"

        # Check for common database errors
        error_str = str(e).lower()
        if "unique constraint" in error_str:
            if "jersey" in error_str:
                error_message = f"Jersey number {player_data.jersey_number} is already taken on this team."
            elif "name" in error_str:
                error_message = f"A player named '{player_data.name}' already exists on this team."
            else:
                error_message = f"Player '{player_data.name}' conflicts with existing player data."
        elif "foreign key" in error_str:
            error_message = f"Invalid team reference for player {player_data.name}."
        elif "not null" in error_str:
            error_message = f"Missing required information for player {player_data.name}."

        raise HTTPException(status_code=400, detail=error_message) from e


@router.get("/stats")
async def get_player_stats_rankings(team_id: int | None = None, session=Depends(get_db)):
    """Get comprehensive player statistics for all players, optionally filtered by team."""
    try:
        stats_service = PlayerStatsService(session)
        player_stats = stats_service.get_player_stats(team_id=team_id)

        return player_stats

    except Exception as e:
        logger.error(f"Error getting player statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve player statistics") from e


@router.get("/{player_id}", response_model=PlayerResponse)
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
                jersey_number=str(player.jersey_number),
                position=player.position,
                height=player.height,
                weight=player.weight,
                year=player.year,
                is_active=player.is_active,
                is_substitute=player.is_substitute,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve player") from e


@router.put("/{player_id}", response_model=PlayerResponse)
async def update_player(
    player_id: int, player_data: PlayerUpdateRequest, current_user: User = Depends(get_current_user)
):
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
                # Cast both sides to string for comparison to handle mixed int/string types in database
                from sqlalchemy import String, cast

                team_id = player_data.team_id or player.team_id
                jersey_str = str(player_data.jersey_number)
                existing_player = (
                    session.query(models.Player)
                    .filter(
                        models.Player.team_id == team_id,
                        cast(models.Player.jersey_number, String) == jersey_str,
                        models.Player.id != player_id,
                        models.Player.is_active,
                    )
                    .first()
                )
                if existing_player:
                    raise HTTPException(
                        status_code=400, detail=f"Jersey number {player_data.jersey_number} already exists on this team"
                    )
                player.jersey_number = str(player_data.jersey_number)
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
            if player_data.is_substitute is not None:
                player.is_substitute = player_data.is_substitute

            session.commit()

            return PlayerResponse(
                id=player.id,
                name=player.name,
                team_id=player.team_id,
                team_name=player.team.name,
                jersey_number=str(player.jersey_number),
                position=player.position,
                height=player.height,
                weight=player.weight,
                year=player.year,
                is_active=player.is_active,
                is_substitute=player.is_substitute,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update player") from e


@router.delete("/{player_id}")
async def delete_player(player_id: int, current_user: User = Depends(get_current_user)):
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


@router.get("/deleted", response_model=list[dict])
async def get_deleted_players():
    """Get all soft-deleted players."""
    try:
        with get_db_session() as session:
            deleted_players = (
                session.query(models.Player)
                .filter(models.Player.is_deleted)
                .order_by(models.Player.deleted_at.desc())
                .all()
            )

            return [
                {
                    "id": player.id,
                    "name": player.name,
                    "jersey_number": str(player.jersey_number),
                    "team_name": player.team.name,
                    "deleted_at": player.deleted_at.isoformat() if player.deleted_at else None,
                }
                for player in deleted_players
            ]
    except Exception as e:
        logger.error(f"Error getting deleted players: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deleted players") from e


@router.get("/{player_id}/stats")
async def get_player_stats(player_id: int, session=Depends(get_db)):
    """Get player statistics including season and career stats."""
    try:
        player = session.query(models.Player).filter(models.Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Get all player's game stats
        game_stats = (
            session.query(models.PlayerGameStats, models.Game)
            .join(models.Game)
            .filter(models.PlayerGameStats.player_id == player_id)
            .order_by(models.Game.date.desc())
            .all()
        )

        # Calculate career totals
        career_stats = {
            "games_played": len(game_stats),
            "total_points": 0,
            "total_ftm": 0,
            "total_fta": 0,
            "total_2pm": 0,
            "total_2pa": 0,
            "total_3pm": 0,
            "total_3pa": 0,
            "total_fouls": 0,
        }

        # Calculate career totals from all games
        for stats, _game in game_stats:
            points = stats_calculator.calculate_points(stats.total_ftm, stats.total_2pm, stats.total_3pm)
            career_stats["total_points"] += points
            career_stats["total_ftm"] += stats.total_ftm
            career_stats["total_fta"] += stats.total_fta
            career_stats["total_2pm"] += stats.total_2pm
            career_stats["total_2pa"] += stats.total_2pa
            career_stats["total_3pm"] += stats.total_3pm
            career_stats["total_3pa"] += stats.total_3pa
            career_stats["total_fouls"] += stats.fouls

        # Get recent games (last 10) with team-level scores
        recent_games = []
        for stats, game in game_stats[:10]:
            points = stats_calculator.calculate_points(stats.total_ftm, stats.total_2pm, stats.total_3pm)

            # Get team scores for this game
            team_id = player.team_id
            opponent_team_id = game.opponent_team_id if game.playing_team_id == team_id else game.playing_team_id

            # Get team stats for this game
            team_stats_query = (
                session.query(
                    func.sum(
                        models.PlayerGameStats.total_ftm
                        + (models.PlayerGameStats.total_2pm * 2)
                        + (models.PlayerGameStats.total_3pm * 3)
                    ).label("total_points")
                )
                .join(models.Player)
                .filter(models.PlayerGameStats.game_id == game.id, models.Player.team_id == team_id)
                .first()
            )

            opponent_stats_query = (
                session.query(
                    func.sum(
                        models.PlayerGameStats.total_ftm
                        + (models.PlayerGameStats.total_2pm * 2)
                        + (models.PlayerGameStats.total_3pm * 3)
                    ).label("total_points")
                )
                .join(models.Player)
                .filter(models.PlayerGameStats.game_id == game.id, models.Player.team_id == opponent_team_id)
                .first()
            )

            team_score = (
                team_stats_query.total_points
                if (team_stats_query and hasattr(team_stats_query, "total_points") and team_stats_query.total_points)
                else 0
            )
            opponent_score = (
                opponent_stats_query.total_points
                if (
                    opponent_stats_query
                    and hasattr(opponent_stats_query, "total_points")
                    and opponent_stats_query.total_points
                )
                else 0
            )

            recent_games.append(
                {
                    "game_id": game.id,
                    "date": game.date.isoformat(),
                    "opponent": game.opponent_team.name,
                    "points": points,  # Player's points
                    "team_score": team_score,  # Team's total points
                    "opponent_score": opponent_score,  # Opponent's total points
                    "win": team_score > opponent_score,  # Team win/loss
                    "ft": f"{stats.total_ftm}/{stats.total_fta}",
                    "ftm": stats.total_ftm,
                    "fta": stats.total_fta,
                    "fg2": f"{stats.total_2pm}/{stats.total_2pa}",
                    "fg2m": stats.total_2pm,
                    "fg2a": stats.total_2pa,
                    "fg3": f"{stats.total_3pm}/{stats.total_3pa}",
                    "fg3m": stats.total_3pm,
                    "fg3a": stats.total_3pa,
                    "fouls": stats.fouls,
                }
            )

        # Calculate career averages
        if career_stats["games_played"] > 0:
            career_stats["ppg"] = round(career_stats["total_points"] / career_stats["games_played"], 1)
            career_stats["fpg"] = round(career_stats["total_fouls"] / career_stats["games_played"], 1)
        else:
            career_stats["ppg"] = 0.0
            career_stats["fpg"] = 0.0

        # Get current season stats using the same pattern as team stats
        season_stats_record = None
        current_season = None
        try:
            from app.data_access.models import PlayerSeasonStats, Season

            stats_service = SeasonStatsService(session)

            # First, check if there's an active season
            active_season = session.query(Season).filter(Season.is_active).first()

            if active_season:
                current_season = active_season.code
                # Update player season stats to ensure they're current
                season_stats_record = stats_service.update_player_season_stats(player_id, current_season)
            else:
                # If no active season, get the most recent season stats for the player
                season_stats_record = (
                    session.query(PlayerSeasonStats)
                    .filter(PlayerSeasonStats.player_id == player_id)
                    .order_by(PlayerSeasonStats.season.desc())
                    .first()
                )
        except Exception as e:
            logger.warning(f"Error getting current season stats for player {player_id}: {e}")
            season_stats_record = None

        if season_stats_record:
            season_stats = {
                "season": season_stats_record.season,
                "games_played": season_stats_record.games_played,
                "total_points": season_stats_record.total_ftm
                + season_stats_record.total_2pm * 2
                + season_stats_record.total_3pm * 3,
                "total_fouls": season_stats_record.total_fouls,
                "total_ftm": season_stats_record.total_ftm,
                "total_fta": season_stats_record.total_fta,
                "total_2pm": season_stats_record.total_2pm,
                "total_2pa": season_stats_record.total_2pa,
                "total_3pm": season_stats_record.total_3pm,
                "total_3pa": season_stats_record.total_3pa,
                "ppg": (
                    round(
                        (
                            season_stats_record.total_ftm
                            + season_stats_record.total_2pm * 2
                            + season_stats_record.total_3pm * 3
                        )
                        / season_stats_record.games_played,
                        1,
                    )
                    if season_stats_record.games_played > 0
                    else 0
                ),
                "fpg": (
                    round(season_stats_record.total_fouls / season_stats_record.games_played, 1)
                    if season_stats_record.games_played > 0
                    else 0
                ),
                "ft_percentage": (
                    round(season_stats_record.total_ftm / season_stats_record.total_fta * 100, 1)
                    if season_stats_record.total_fta > 0
                    else 0
                ),
                "fg2_percentage": (
                    round(season_stats_record.total_2pm / season_stats_record.total_2pa * 100, 1)
                    if season_stats_record.total_2pa > 0
                    else 0
                ),
                "fg3_percentage": (
                    round(season_stats_record.total_3pm / season_stats_record.total_3pa * 100, 1)
                    if season_stats_record.total_3pa > 0
                    else 0
                ),
            }
        else:
            season_stats = None

        return {
            "player": {
                "id": player.id,
                "name": player.name,
                "jersey_number": str(player.jersey_number),
                "position": player.position,
                "height": player.height,
                "weight": player.weight,
                "year": player.year,
                "team_name": player.team.name,
                "thumbnail_image": player.thumbnail_image,
                "player_of_the_week_awards": player.player_of_the_week_awards,  # Legacy counter for backward compatibility
                "potw_summary": _get_potw_summary(session, player.id),
            },
            "career_stats": career_stats,
            "season_stats": season_stats,
            "recent_games": recent_games,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get player stats") from e


@router.post("/{player_id}/portrait")
@invalidate_cache_after
async def upload_player_portrait(
    player_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session=Depends(get_db),
):
    """Upload a portrait image for a player."""
    try:
        # Validate file before processing
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "INVALID_FILE_TYPE",
                    "message": "Please upload an image file (JPG, PNG, or WebP)",
                    "accepted_types": ["image/jpeg", "image/png", "image/webp"],
                },
            )

        # Check file size (5MB limit) - skip if in test environment with mock objects
        try:
            file_size = 0
            if hasattr(file, "size") and file.size and isinstance(file.size, int):
                file_size = file.size
            elif file.file and hasattr(file.file, "tell") and hasattr(file.file, "seek"):
                # Get file size by seeking to end
                current_pos = file.file.tell()
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(current_pos)  # Reset position

            max_size = 5 * 1024 * 1024  # 5MB
            if file_size > max_size:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "FILE_TOO_LARGE",
                        "message": f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size (5MB)",
                        "max_size_mb": 5,
                    },
                )
        except (AttributeError, TypeError):
            # Skip file size check if we can't determine it (e.g., in tests with mocks)
            pass

        # Verify player exists
        player = session.query(models.Player).filter(models.Player.id == player_id).first()
        if not player:
            raise HTTPException(
                status_code=404,
                detail={"error": "PLAYER_NOT_FOUND", "message": f"Player with ID {player_id} not found"},
            )

        # Process the portrait using the image processing service
        from app.services.image_processing_service import ImageProcessingService

        try:
            portrait_url = await ImageProcessingService.process_player_portrait(player_id, file)
        except HTTPException as e:
            # Re-raise image processing errors with enhanced details
            if e.status_code == 400:
                raise HTTPException(
                    status_code=422,
                    detail={"error": "IMAGE_PROCESSING_FAILED", "message": str(e.detail), "player_id": player_id},
                ) from e
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "PROCESSING_ERROR",
                        "message": "Failed to process image file",
                        "player_id": player_id,
                    },
                ) from e

        # Update the player's portrait filename in the database
        portrait_filename = ImageProcessingService.update_player_portrait_filename(player_id)
        player.thumbnail_image = portrait_filename
        session.commit()

        # Clear template cache for this player
        from app.web_ui.templates_config import clear_player_portrait_cache

        clear_player_portrait_cache(player_id)

        logger.info(f"Successfully uploaded portrait for player {player_id}")
        return {"success": True, "portrait_url": portrait_url, "player_id": player_id, "filename": portrait_filename}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading player portrait for player {player_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "UPLOAD_FAILED",
                "message": "An unexpected error occurred while uploading the portrait",
                "player_id": player_id,
            },
        ) from e


@router.delete("/{player_id}/portrait")
async def delete_player_portrait(
    player_id: int, current_user: User = Depends(get_current_user), session=Depends(get_db)
):
    """Delete a player's portrait image."""
    try:
        # Verify player exists
        player = session.query(models.Player).filter(models.Player.id == player_id).first()
        if not player:
            raise HTTPException(
                status_code=404,
                detail={"error": "PLAYER_NOT_FOUND", "message": f"Player with ID {player_id} not found"},
            )

        if not player.thumbnail_image:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NO_PORTRAIT_TO_DELETE",
                    "message": f"Player {player.name} does not have a portrait to delete",
                    "player_id": player_id,
                },
            )

        # Store the filename for logging
        deleted_filename = player.thumbnail_image

        # Delete the portrait using the image processing service
        from app.services.image_processing_service import ImageProcessingService

        try:
            ImageProcessingService.delete_player_portrait(player_id)
        except HTTPException as e:
            # Re-raise service errors with enhanced details
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "error": "DELETE_FAILED",
                    "message": f"Failed to delete portrait files: {e.detail}",
                    "player_id": player_id,
                    "filename": deleted_filename,
                },
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "FILE_DELETE_ERROR",
                    "message": "Failed to delete portrait files from storage",
                    "player_id": player_id,
                    "filename": deleted_filename,
                },
            ) from e

        # Clear the portrait filename in the database
        player.thumbnail_image = None
        session.commit()

        # Clear template cache for this player
        from app.web_ui.templates_config import clear_player_portrait_cache

        clear_player_portrait_cache(player_id)

        logger.info(f"Successfully deleted portrait for player {player_id} (was: {deleted_filename})")
        return {
            "success": True,
            "message": "Portrait deleted successfully",
            "player_id": player_id,
            "deleted_filename": deleted_filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting player portrait for player {player_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DELETE_FAILED",
                "message": "An unexpected error occurred while deleting the portrait",
                "player_id": player_id,
            },
        ) from e


# Legacy endpoint for backward compatibility
@router.post("/{player_id}/upload-image")
async def upload_player_image(
    player_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session=Depends(get_db),
):
    """Legacy endpoint for uploading player images. Redirects to portrait endpoint."""
    return await upload_player_portrait(player_id, file, current_user, session)


@router.post("/{player_id}/restore")
async def restore_player(player_id: int, current_user: User = Depends(require_admin)):
    """Restore a soft-deleted player."""
    try:
        with get_db_session() as session:
            player = session.query(models.Player).filter_by(id=player_id).first()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")

            if not player.is_deleted:
                raise HTTPException(status_code=400, detail="Player is not deleted")

            player.is_deleted = False
            player.deleted_at = None
            player.deleted_by = None
            player.is_active = True

            # Log the restore
            from app.services.audit_log_service import AuditLogService

            audit_service = AuditLogService(session)
            audit_service.log_restore(
                entity_type="player",
                entity_id=player_id,
                restored_values={"is_deleted": False, "is_active": True},
                description=f"Restored player {player_id}",
            )

            session.commit()
            return {"success": True, "message": "Player restored successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring player: {e}")
        raise HTTPException(status_code=500, detail="Failed to restore player") from e
