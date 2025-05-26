"""Teams router for Basketball Stats Tracker."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.data_access.models import Team
from app.repositories import PlayerRepository, TeamRepository
from app.services.audit_log_service import AuditLogService

from ..dependencies import get_db, get_player_repository, get_team_repository
from ..schemas import PlayerResponse, TeamCreateRequest, TeamDetailResponse, TeamResponse, TeamUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/teams", tags=["teams"])


@router.get("", response_model=list[dict[str, Any]])
async def list_teams(team_repo: TeamRepository = Depends(get_team_repository)):  # noqa: B008
    """Get a list of all teams."""
    try:
        teams: list = team_repo.get_all()
        return [
            {
                "id": team.id,
                "name": team.name,
                "display_name": team.display_name,
            }
            for team in teams
        ]
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve teams") from e


@router.get("/detail", response_model=list[TeamResponse])
async def list_teams_with_counts(team_repo: TeamRepository = Depends(get_team_repository)):  # noqa: B008
    """Get a list of all teams with player counts."""
    try:
        teams_with_counts = team_repo.get_with_player_count()
        return [
            TeamResponse(
                id=team["id"],
                name=team["name"],
                display_name=team.get("display_name"),
                player_count=team["player_count"],
            )
            for team in teams_with_counts
        ]
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve teams") from e


@router.get("/{team_id}", response_model=dict[str, Any])
async def get_team(
    team_id: int,
    team_repo: TeamRepository = Depends(get_team_repository),  # noqa: B008
    player_repo: PlayerRepository = Depends(get_player_repository),  # noqa: B008
):
    """Get detailed information about a specific team."""
    try:
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Get team roster
        players = player_repo.get_team_players(team_id)

        return {
            "id": team.id,
            "name": team.name,
            "display_name": team.display_name,
            "roster": [
                {
                    "id": player.id,
                    "name": player.name,
                    "jersey_number": player.jersey_number,
                }
                for player in players
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team") from e


@router.get("/{team_id}/detail", response_model=TeamDetailResponse)
async def get_team_detail(
    team_id: int,
    team_repo: TeamRepository = Depends(get_team_repository),  # noqa: B008
    player_repo: PlayerRepository = Depends(get_player_repository),  # noqa: B008
):
    """Get detailed information about a specific team including players."""
    try:
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        players = player_repo.get_team_players(team_id, active_only=True)

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

        return TeamDetailResponse(id=team.id, name=team.name, display_name=team.display_name, players=player_responses)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team") from e


@router.post("/new", response_model=TeamResponse)
async def create_team(team_data: TeamCreateRequest, team_repo: TeamRepository = Depends(get_team_repository)):  # noqa: B008
    """Create a new team."""
    try:
        # Check if team name already exists
        existing_team = team_repo.get_by_name(team_data.name)
        if existing_team:
            raise HTTPException(status_code=400, detail="Team name already exists")

        team: Team = team_repo.create(name=team_data.name, display_name=team_data.display_name)
        return TeamResponse(id=team.id, name=team.name, display_name=team.display_name, player_count=0)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        raise HTTPException(status_code=500, detail="Failed to create team") from e


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdateRequest,
    team_repo: TeamRepository = Depends(get_team_repository),  # noqa: B008
):
    """Update a team."""
    try:
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Build update kwargs - only include fields that are not None
        update_kwargs = {}

        # Check if new name conflicts with existing team
        if team_data.name is not None:
            if team_data.name != team.name:
                existing_team = team_repo.get_by_name(team_data.name)
                if existing_team and existing_team.id != team_id:
                    raise HTTPException(status_code=400, detail="Team name already exists")
            update_kwargs["name"] = team_data.name

        if team_data.display_name is not None:
            update_kwargs["display_name"] = team_data.display_name

        updated_team = team_repo.update(team_id, **update_kwargs)
        if not updated_team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Get player count
        teams_with_counts = team_repo.get_with_player_count()
        player_count = next((t["player_count"] for t in teams_with_counts if t["id"] == team_id), 0)

        return TeamResponse(
            id=updated_team.id,
            name=updated_team.name,
            display_name=updated_team.display_name,
            player_count=player_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update team") from e


@router.delete("/{team_id}")
async def delete_team(team_id: int, team_repo: TeamRepository = Depends(get_team_repository)):  # noqa: B008
    """Delete a team and all its players."""
    try:
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Check if team has games
        if team_repo.has_games(team_id):
            raise HTTPException(
                status_code=400, detail="Cannot delete team with existing games. Archive the team instead."
            )

        team_repo.delete(team_id)
        return {"message": "Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete team") from e


@router.get("/deleted", response_model=list[dict[str, Any]])
async def get_deleted_teams(team_repo: TeamRepository = Depends(get_team_repository)):  # noqa: B008
    """Get all soft-deleted teams."""
    try:
        deleted_teams = team_repo.get_deleted_teams()
        return [
            {
                "id": team.id,
                "name": team.name,
                "deleted_at": team.deleted_at.isoformat() if team.deleted_at else None,
            }
            for team in deleted_teams
        ]
    except Exception as e:
        logger.error(f"Error getting deleted teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deleted teams") from e


@router.post("/{team_id}/restore")
async def restore_team(team_id: int, team_repo: TeamRepository = Depends(get_team_repository), db=Depends(get_db)):  # noqa: B008
    """Restore a soft-deleted team."""
    try:
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        if not team.is_deleted:
            raise HTTPException(status_code=400, detail="Team is not deleted")

        team.is_deleted = False
        team.deleted_at = None
        team.deleted_by = None

        # Log the restore
        audit_service = AuditLogService(db)
        audit_service.log_restore(
            entity_type="team",
            entity_id=team_id,
            restored_values={"is_deleted": False},
            description=f"Restored team {team_id}",
        )

        db.commit()
        return {"success": True, "message": "Team restored successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring team: {e}")
        raise HTTPException(status_code=500, detail="Failed to restore team") from e
