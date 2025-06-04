"""Teams router for Basketball Stats Tracker."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.data_access.models import Team
from app.repositories import PlayerRepository, TeamRepository
from app.services.audit_log_service import AuditLogService
from app.services.image_processing_service import ImageProcessingService
from app.services.season_stats_service import SeasonStatsService

from ..dependencies import get_db, get_player_repository, get_team_repository
from ..schemas import (
    DeletedTeamResponse,
    PlayerResponse,
    RosterPlayer,
    TeamBasicResponse,
    TeamCreateRequest,
    TeamDetailResponse,
    TeamResponse,
    TeamStatsResponse,
    TeamUpdateRequest,
    TeamWithRosterResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/teams", tags=["teams"])


def calculate_derived_stats(stats: dict) -> dict:
    """Calculate derived statistics like averages and percentages."""
    derived = {}

    if stats["games_played"] > 0:
        derived["win_percentage"] = round(stats["wins"] / stats["games_played"] * 100, 1)
        derived["ppg"] = round(stats["total_points_for"] / stats["games_played"], 1)
        derived["opp_ppg"] = round(stats["total_points_against"] / stats["games_played"], 1)
        derived["point_diff"] = round(derived["ppg"] - derived["opp_ppg"], 1)
    else:
        derived["win_percentage"] = 0
        derived["ppg"] = 0
        derived["opp_ppg"] = 0
        derived["point_diff"] = 0

    return derived


def calculate_shooting_percentages(stats: dict) -> dict:
    """Calculate shooting percentages for different shot types."""
    percentages = {}

    # Free throw percentage
    percentages["ft_percentage"] = (
        round(stats["total_ftm"] / stats["total_fta"] * 100, 1) if stats["total_fta"] > 0 else 0
    )

    # 2-point field goal percentage
    percentages["fg2_percentage"] = (
        round(stats["total_2pm"] / stats["total_2pa"] * 100, 1) if stats["total_2pa"] > 0 else 0
    )

    # 3-point field goal percentage
    percentages["fg3_percentage"] = (
        round(stats["total_3pm"] / stats["total_3pa"] * 100, 1) if stats["total_3pa"] > 0 else 0
    )

    return percentages


@router.get("", response_model=list[TeamBasicResponse])
async def list_teams(team_repo: TeamRepository = Depends(get_team_repository)):  # noqa: B008
    """Get a list of all teams."""
    try:
        teams: list = team_repo.get_all()
        return [
            TeamBasicResponse(
                id=team.id,
                name=team.name,
                display_name=team.display_name,
            )
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


@router.get("/{team_id}", response_model=TeamWithRosterResponse)
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

        return TeamWithRosterResponse(
            id=team.id,
            name=team.name,
            display_name=team.display_name,
            roster=[
                RosterPlayer(
                    id=player.id,
                    name=player.name,
                    jersey_number=player.jersey_number,
                )
                for player in players
            ],
        )
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


@router.get("/{team_id}/stats", response_model=TeamStatsResponse)
async def get_team_stats(
    team_id: int,
    team_repo: TeamRepository = Depends(get_team_repository),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    """Get team statistics including career and current season stats."""
    try:
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        stats_service = SeasonStatsService(db)

        # Get current season stats
        season_stats = None
        current_season = None
        try:
            # Get the active season from the Season table
            from sqlalchemy import desc, func

            from app.data_access.models import Season

            active_season = db.query(Season).filter(Season.is_active).first()

            if active_season:
                current_season = active_season.code
                season_stats = stats_service.update_team_season_stats(team_id, current_season)
        except Exception as e:
            logger.warning(f"Error getting current season stats for team {team_id}: {e}")

        # Get all-time/career stats by aggregating all season stats
        from app.data_access.models import TeamSeasonStats

        all_season_stats = db.query(TeamSeasonStats).filter(TeamSeasonStats.team_id == team_id).all()

        # Calculate career totals
        career_stats = {
            "games_played": sum(s.games_played for s in all_season_stats),
            "wins": sum(s.wins for s in all_season_stats),
            "losses": sum(s.losses for s in all_season_stats),
            "total_points_for": sum(s.total_points_for for s in all_season_stats),
            "total_points_against": sum(s.total_points_against for s in all_season_stats),
            "total_ftm": sum(s.total_ftm for s in all_season_stats),
            "total_fta": sum(s.total_fta for s in all_season_stats),
            "total_2pm": sum(s.total_2pm for s in all_season_stats),
            "total_2pa": sum(s.total_2pa for s in all_season_stats),
            "total_3pm": sum(s.total_3pm for s in all_season_stats),
            "total_3pa": sum(s.total_3pa for s in all_season_stats),
        }

        # Calculate derived stats
        career_stats.update(calculate_derived_stats(career_stats))

        # Calculate shooting percentages
        career_stats.update(calculate_shooting_percentages(career_stats))

        # Format season stats if available
        formatted_season_stats = None
        if season_stats:
            formatted_season_stats = {
                "season": current_season,
                "games_played": season_stats.games_played,
                "wins": season_stats.wins,
                "losses": season_stats.losses,
                "total_points_for": season_stats.total_points_for,
                "total_points_against": season_stats.total_points_against,
                "total_ftm": season_stats.total_ftm,
                "total_fta": season_stats.total_fta,
                "total_2pm": season_stats.total_2pm,
                "total_2pa": season_stats.total_2pa,
                "total_3pm": season_stats.total_3pm,
                "total_3pa": season_stats.total_3pa,
            }

            # Calculate derived stats and shooting percentages using helper functions
            formatted_season_stats.update(calculate_derived_stats(formatted_season_stats))
            formatted_season_stats.update(calculate_shooting_percentages(formatted_season_stats))

        # Get recent games for team
        from app.data_access.models import Game, Player, PlayerGameStats

        recent_games = (
            db.query(Game)
            .filter((Game.playing_team_id == team_id) | (Game.opponent_team_id == team_id))
            .order_by(desc(Game.date))
            .limit(10)
            .all()
        )

        recent_games_data = []

        # Batch query to fetch and aggregate player stats for all games in recent_games
        stats_query = (
            db.query(
                PlayerGameStats.game_id,
                Player.team_id,
                func.sum(PlayerGameStats.total_ftm).label("total_ftm"),
                func.sum(PlayerGameStats.total_fta).label("total_fta"),
                func.sum(PlayerGameStats.total_2pm).label("total_2pm"),
                func.sum(PlayerGameStats.total_2pa).label("total_2pa"),
                func.sum(PlayerGameStats.total_3pm).label("total_3pm"),
                func.sum(PlayerGameStats.total_3pa).label("total_3pa"),
                func.sum(
                    PlayerGameStats.total_ftm + (PlayerGameStats.total_2pm * 2) + (PlayerGameStats.total_3pm * 3)
                ).label("total_points"),
            )
            .join(Player)
            .filter(PlayerGameStats.game_id.in_([game.id for game in recent_games]))
            .group_by(PlayerGameStats.game_id, Player.team_id)
            .all()
        )

        # Organize stats by game_id and team_id for quick lookup
        stats_by_game_and_team = {(stat.game_id, stat.team_id): stat for stat in stats_query}

        for game in recent_games:
            # Get opponent info first
            opponent_team_id = game.opponent_team_id if game.playing_team_id == team_id else game.playing_team_id
            opponent_team = team_repo.get_by_id(opponent_team_id)
            opponent_name = opponent_team.display_name or opponent_team.name if opponent_team else "Unknown"

            team_stats = stats_by_game_and_team.get((game.id, team_id), None)
            opponent_stats = stats_by_game_and_team.get((game.id, opponent_team_id), None)

            team_points = team_stats.total_points if team_stats else 0
            team_ftm = team_stats.total_ftm if team_stats else 0
            team_fta = team_stats.total_fta if team_stats else 0
            team_2pm = team_stats.total_2pm if team_stats else 0
            team_2pa = team_stats.total_2pa if team_stats else 0
            team_3pm = team_stats.total_3pm if team_stats else 0
            team_3pa = team_stats.total_3pa if team_stats else 0

            # Calculate opponent points
            opponent_points = opponent_stats.total_points if opponent_stats else 0

            recent_games_data.append(
                {
                    "game_id": game.id,
                    "date": game.date.isoformat(),
                    "opponent": opponent_name,
                    "team_points": team_points,
                    "opponent_points": opponent_points,
                    "win": team_points > opponent_points,
                    "ft": f"{team_ftm}/{team_fta}",
                    "fg2": f"{team_2pm}/{team_2pa}",
                    "fg3": f"{team_3pm}/{team_3pa}",
                    "ft_percentage": round(team_ftm / team_fta * 100) if team_fta > 0 else 0,
                    "fg2_percentage": round(team_2pm / team_2pa * 100) if team_2pa > 0 else 0,
                    "fg3_percentage": round(team_3pm / team_3pa * 100) if team_3pa > 0 else 0,
                }
            )

        return {
            "team": {
                "id": team.id,
                "name": team.name,
                "display_name": team.display_name,
            },
            "career_stats": career_stats,
            "season_stats": formatted_season_stats,
            "recent_games": recent_games_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving team stats for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team statistics") from e


@router.post("/new", response_model=TeamResponse)
async def create_team(
    team_data: TeamCreateRequest,
    team_repo: TeamRepository = Depends(get_team_repository),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
):
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
    current_user: User = Depends(get_current_user),  # noqa: B008
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
async def delete_team(
    team_id: int,
    team_repo: TeamRepository = Depends(get_team_repository),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
):
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


@router.get("/deleted", response_model=list[DeletedTeamResponse])
async def get_deleted_teams(team_repo: TeamRepository = Depends(get_team_repository)):  # noqa: B008
    """Get all soft-deleted teams."""
    try:
        deleted_teams = team_repo.get_deleted_teams()
        return [
            DeletedTeamResponse(
                id=team.id,
                name=team.name,
                deleted_at=team.deleted_at.isoformat() if team.deleted_at else None,
            )
            for team in deleted_teams
        ]
    except Exception as e:
        logger.error(f"Error getting deleted teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deleted teams") from e


@router.post("/{team_id}/restore")
async def restore_team(
    team_id: int,
    team_repo: TeamRepository = Depends(get_team_repository),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
    current_user: User = Depends(require_admin),  # noqa: B008
):
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


@router.post("/{team_id}/logo")
async def upload_team_logo(
    team_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db=Depends(get_db)
):
    """Upload a logo image for a team."""
    try:
        # Verify team exists
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Store old logo filename for auditing
        old_logo = team.logo_filename

        # Process and store the logo in multiple sizes
        logo_urls = await ImageProcessingService.process_team_logo(team_id, file)

        # Update team record with logo filename
        logo_filename = ImageProcessingService.update_team_logo_filename(team_id)
        team.logo_filename = logo_filename

        # Log the upload
        audit_service = AuditLogService(db)
        audit_service.log_update(
            entity_type="team",
            entity_id=team_id,
            old_values={"logo_filename": old_logo},
            new_values={"logo_filename": logo_filename},
            description=f"Uploaded logo for team {team.name}",
        )

        db.commit()

        return {
            "success": True,
            "message": "Logo uploaded successfully",
            "logo_urls": logo_urls,
            "logo_filename": logo_filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading team logo for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload logo") from e


@router.delete("/{team_id}/logo")
async def delete_team_logo(team_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Delete the logo for a team."""
    try:
        # Verify team exists
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        if not team.logo_filename:
            raise HTTPException(status_code=400, detail="Team has no logo to delete")

        # Delete logo files from filesystem
        ImageProcessingService.delete_team_logo(team_id)

        # Update team record
        old_logo = team.logo_filename
        team.logo_filename = None

        # Log the deletion
        audit_service = AuditLogService(db)
        audit_service.log_update(
            entity_type="team",
            entity_id=team_id,
            old_values={"logo_filename": old_logo},
            new_values={"logo_filename": None},
            description=f"Deleted logo for team {team.name}",
        )

        db.commit()

        return {"success": True, "message": "Logo deleted successfully", "deleted_logo": old_logo}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team logo for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete logo") from e
