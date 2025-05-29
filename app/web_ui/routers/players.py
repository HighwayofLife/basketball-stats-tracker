"""Players router for Basketball Stats Tracker."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import Integer, func

from app.data_access import models
from app.data_access.db_session import get_db_session
from app.utils import stats_calculator

from ..schemas import PlayerCreateRequest, PlayerResponse, PlayerUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/players", tags=["players"])


@router.get("/list", response_model=list[PlayerResponse])
async def list_players(team_id: int | None = None, active_only: bool = True):
    """Get a list of players with optional team filtering."""
    try:
        with get_db_session() as session:
            query = session.query(models.Player, models.Team).join(models.Team, models.Player.team_id == models.Team.id)

            if team_id:
                query = query.filter(models.Player.team_id == team_id)

            if active_only:
                query = query.filter(models.Player.is_active)

            players_teams = query.order_by(models.Team.name, func.cast(models.Player.jersey_number, Integer)).all()

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


@router.post("/new", response_model=PlayerResponse)
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


@router.put("/{player_id}", response_model=PlayerResponse)
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
                        models.Player.is_active,
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


@router.delete("/{player_id}")
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
                    "jersey_number": player.jersey_number,
                    "team_name": player.team.name,
                    "deleted_at": player.deleted_at.isoformat() if player.deleted_at else None,
                }
                for player in deleted_players
            ]
    except Exception as e:
        logger.error(f"Error getting deleted players: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deleted players") from e


@router.get("/{player_id}/stats")
async def get_player_stats(player_id: int):
    """Get player statistics including season and career stats."""
    try:
        with get_db_session() as session:
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

            recent_games = []
            for stats, game in game_stats[:10]:  # Last 10 games
                points = stats_calculator.calculate_points(stats.total_ftm, stats.total_2pm, stats.total_3pm)
                career_stats["total_points"] += points
                career_stats["total_ftm"] += stats.total_ftm
                career_stats["total_fta"] += stats.total_fta
                career_stats["total_2pm"] += stats.total_2pm
                career_stats["total_2pa"] += stats.total_2pa
                career_stats["total_3pm"] += stats.total_3pm
                career_stats["total_3pa"] += stats.total_3pa
                career_stats["total_fouls"] += stats.fouls

                recent_games.append(
                    {
                        "game_id": game.id,
                        "date": game.date.isoformat(),
                        "opponent": game.opponent_team.name,
                        "points": points,
                        "ft": f"{stats.total_ftm}/{stats.total_fta}",
                        "fg2": f"{stats.total_2pm}/{stats.total_2pa}",
                        "fg3": f"{stats.total_3pm}/{stats.total_3pa}",
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

            # Get season stats
            current_season = "2024-2025"  # You might want to calculate this dynamically
            season_stats_record = (
                session.query(models.PlayerSeasonStats).filter_by(player_id=player_id, season=current_season).first()
            )

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
                    "ppg": round(
                        (
                            season_stats_record.total_ftm
                            + season_stats_record.total_2pm * 2
                            + season_stats_record.total_3pm * 3
                        )
                        / season_stats_record.games_played,
                        1,
                    )
                    if season_stats_record.games_played > 0
                    else 0,
                    "fpg": round(season_stats_record.total_fouls / season_stats_record.games_played, 1)
                    if season_stats_record.games_played > 0
                    else 0,
                    "ft_percentage": round(season_stats_record.total_ftm / season_stats_record.total_fta * 100, 1)
                    if season_stats_record.total_fta > 0
                    else 0,
                    "fg2_percentage": round(season_stats_record.total_2pm / season_stats_record.total_2pa * 100, 1)
                    if season_stats_record.total_2pa > 0
                    else 0,
                    "fg3_percentage": round(season_stats_record.total_3pm / season_stats_record.total_3pa * 100, 1)
                    if season_stats_record.total_3pa > 0
                    else 0,
                }
            else:
                season_stats = None

            return {
                "player": {
                    "id": player.id,
                    "name": player.name,
                    "jersey_number": player.jersey_number,
                    "position": player.position,
                    "height": player.height,
                    "weight": player.weight,
                    "year": player.year,
                    "team_name": player.team.name,
                    "thumbnail_image": player.thumbnail_image,
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


@router.post("/{player_id}/upload-image")
async def upload_player_image(player_id: int, file: UploadFile = File(...)):
    """Upload a thumbnail image for a player."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image file.")

        # Validate file size (max 5MB)
        file_size = 0
        contents = await file.read()
        file_size = len(contents)
        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

        # Create upload directory if it doesn't exist
        upload_dir = Path("app/web_ui/static/uploads/players")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        file_extension = os.path.splitext(file.filename)[1]
        if file_extension.lower() not in [".jpg", ".jpeg", ".png"]:
            raise HTTPException(status_code=400, detail="Invalid file format. Only JPG and PNG files are allowed.")

        filename = f"player_{player_id}{file_extension}"
        file_path = upload_dir / filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)

        # Update player record
        with get_db_session() as session:
            player = session.query(models.Player).filter(models.Player.id == player_id).first()
            if not player:
                # Clean up uploaded file
                if file_path.exists():
                    file_path.unlink()
                raise HTTPException(status_code=404, detail="Player not found")

            # Remove old image if exists
            if player.thumbnail_image:
                old_path = Path("app/web_ui/static") / player.thumbnail_image
                if old_path.exists():
                    old_path.unlink()

            player.thumbnail_image = f"uploads/players/{filename}"
            session.commit()

            return {"success": True, "message": "Image uploaded successfully", "image_path": player.thumbnail_image}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading player image: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image") from e


@router.post("/{player_id}/restore")
async def restore_player(player_id: int):
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
