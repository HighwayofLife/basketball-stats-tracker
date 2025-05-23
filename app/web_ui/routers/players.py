"""Players router for Basketball Stats Tracker."""

import logging

from fastapi import APIRouter, HTTPException

from app.data_access import models
from app.data_access.db_session import get_db_session

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
                .filter(models.Player.is_deleted == True)
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
