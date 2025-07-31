"""API endpoints for playoff bracket functionality."""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models import User
from app.dependencies import get_db
from app.services.playoffs_service import GameNotFoundError, InvalidSeasonError, PlayoffsService

router = APIRouter(prefix="/v1/playoffs", tags=["playoffs"])


# Pydantic models for request/response
class PlayoffConfigRequest(BaseModel):
    """Request model for playoff configuration."""

    season: str = Field(..., pattern=r"^20[0-9]{2}$", description="Season year (e.g., '2025')")
    num_teams: int = Field(..., ge=2, le=64, description="Number of teams (2-64)")
    bracket_type: Literal["single_elimination"] = Field(..., description="Bracket type")

    @validator("num_teams")
    def validate_power_of_two(cls, v):
        """Ensure number of teams is a power of 2."""
        if v & (v - 1) != 0:
            raise ValueError("Number of teams must be a power of 2")
        return v


class PlayoffConfigResponse(BaseModel):
    """Response model for playoff configuration."""

    season: str
    num_teams: int
    bracket_type: str
    num_rounds: int
    is_active: bool


class TeamSeedUpdate(BaseModel):
    """Model for team seed updates."""

    team_id: int
    seed: int


class TeamSeedResponse(BaseModel):
    """Response model for team with seed."""

    id: int
    name: str
    seed: int | None
    record: str | None


@router.get("/bracket")
def get_playoff_bracket(
    season: str | None = Query(None, description="Season year (e.g., '2025')"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get playoff bracket data.

    Args:
        season: Optional season year filter
        db: Database session

    Returns:
        Playoff bracket structure with teams and scores
    """
    try:
        service = PlayoffsService(db)
        return service.get_playoff_bracket(season=season)
    except InvalidSeasonError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/games/{game_id}/mark-playoff")
def mark_game_as_playoff(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Mark a game as a playoff game.

    Args:
        game_id: ID of the game to mark as playoff
        db: Database session

    Returns:
        Success message with game ID
    """
    try:
        service = PlayoffsService(db)
        game = service.mark_game_as_playoff(game_id)
        return {
            "success": True,
            "message": f"Game {game_id} marked as playoff game",
            "game_id": game.id,
        }
    except GameNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/games/{game_id}/mark-playoff")
def unmark_game_as_playoff(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Unmark a game as a playoff game.

    Args:
        game_id: ID of the game to unmark as playoff
        db: Database session

    Returns:
        Success message with game ID
    """
    try:
        service = PlayoffsService(db)
        game = service.unmark_game_as_playoff(game_id)
        return {
            "success": True,
            "message": f"Game {game_id} no longer marked as playoff game",
            "game_id": game.id,
        }
    except GameNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/config", response_model=PlayoffConfigResponse)
def get_playoff_config(
    season: str | None = Query("2025", description="Season year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> PlayoffConfigResponse:
    """Get playoff configuration for a season.

    Args:
        season: Season year
        db: Database session
        current_user: Current admin user

    Returns:
        Playoff configuration
    """
    from app.data_access.models import PlayoffConfig

    config = db.query(PlayoffConfig).filter(PlayoffConfig.season == season, PlayoffConfig.is_active).first()

    if not config:
        # Return default configuration
        return PlayoffConfigResponse(
            season=season, num_teams=8, bracket_type="single_elimination", num_rounds=3, is_active=True
        )

    return PlayoffConfigResponse(
        season=config.season,
        num_teams=config.num_teams,
        bracket_type=config.bracket_type,
        num_rounds=config.num_rounds,
        is_active=config.is_active,
    )


@router.post("/config", response_model=PlayoffConfigResponse)
def save_playoff_config(
    config_data: PlayoffConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> PlayoffConfigResponse:
    """Save playoff configuration for a season.

    Args:
        config_data: Configuration data
        db: Database session
        current_user: Current admin user

    Returns:
        Saved configuration
    """
    from sqlalchemy.exc import IntegrityError

    from app.data_access.models import PlayoffConfig

    # Calculate number of rounds based on number of teams
    num_rounds = 1
    teams = config_data.num_teams
    while teams > 2:
        teams //= 2
        num_rounds += 1

    # Use a query with FOR UPDATE to lock the row during the transaction
    existing_config = (
        db.query(PlayoffConfig)
        .filter(PlayoffConfig.season == config_data.season, PlayoffConfig.is_active)
        .with_for_update()
        .first()
    )

    if existing_config:
        # Update the existing config instead of creating a new one
        existing_config.num_teams = config_data.num_teams
        existing_config.num_rounds = num_rounds
        existing_config.bracket_type = config_data.bracket_type
        existing_config.updated_at = datetime.utcnow()
        config = existing_config
    else:
        # Create new config
        config = PlayoffConfig(
            season=config_data.season,
            num_teams=config_data.num_teams,
            num_rounds=num_rounds,
            bracket_type=config_data.bracket_type,
            is_active=True,
        )
        db.add(config)

    try:
        db.commit()
        db.refresh(config)
    except IntegrityError:
        db.rollback()
        # Handle race condition where another request created the config
        # Retry by fetching the existing config
        existing_config = (
            db.query(PlayoffConfig).filter(PlayoffConfig.season == config_data.season, PlayoffConfig.is_active).first()
        )
        if existing_config:
            existing_config.num_teams = config_data.num_teams
            existing_config.num_rounds = num_rounds
            existing_config.bracket_type = config_data.bracket_type
            existing_config.updated_at = datetime.utcnow()
            config = existing_config
            db.commit()
            db.refresh(config)
        else:
            raise HTTPException(status_code=500, detail="Failed to save playoff configuration") from None

    return PlayoffConfigResponse(
        season=config.season,
        num_teams=config.num_teams,
        bracket_type=config.bracket_type,
        num_rounds=config.num_rounds,
        is_active=config.is_active,
    )


@router.get("/seeds", response_model=list[TeamSeedResponse])
def get_team_seeds(
    season: str | None = Query("2025", description="Season year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[TeamSeedResponse]:
    """Get all teams with their playoff seeds.

    Args:
        season: Season year
        db: Database session
        current_user: Current admin user

    Returns:
        List of teams with seeds
    """
    from app.data_access.models import Team

    teams = db.query(Team).order_by(Team.playoff_seed.nulls_last(), Team.name).all()

    return [
        TeamSeedResponse(
            id=team.id,
            name=team.name,
            seed=team.playoff_seed,
            record=f"{getattr(team, 'wins', 0)}-{getattr(team, 'losses', 0)}" if hasattr(team, "wins") else None,
        )
        for team in teams
    ]


@router.post("/seeds")
def save_team_seeds(
    seed_changes: dict[str, int],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Save team playoff seeds.

    Args:
        seed_changes: Dictionary mapping team_id to seed number
        db: Database session
        current_user: Current admin user

    Returns:
        Success message
    """
    from app.data_access.models import Team

    updated_count = 0
    errors = []

    # Validate all inputs first
    for team_id_str, seed in seed_changes.items():
        try:
            team_id = int(team_id_str)
        except ValueError:
            errors.append(f"Invalid team ID: {team_id_str}")
            continue

        # Validate seed number (should be positive)
        if seed < 1:
            errors.append(f"Invalid seed number {seed} for team ID {team_id_str}. Seed must be positive.")
            continue

    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Process valid updates
    for team_id_str, seed in seed_changes.items():
        try:
            team_id = int(team_id_str)
            team = db.query(Team).filter(Team.id == team_id).first()

            if team:
                team.playoff_seed = seed
                updated_count += 1
            else:
                errors.append(f"Team with ID {team_id} not found")
        except Exception as e:
            errors.append(f"Error updating team {team_id_str}: {str(e)}")

    if errors:
        db.rollback()
        raise HTTPException(status_code=400, detail={"errors": errors})

    db.commit()

    return {"success": True, "message": f"Updated seeds for {updated_count} teams", "updated_count": updated_count}
