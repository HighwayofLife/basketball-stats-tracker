"""
CRUD operations for Team model.
"""

from sqlalchemy.orm import Session

from app.data_access.transaction import transaction
from app.data_access.models import Team


def create_team(db: Session, team_name: str, display_name: str | None = None) -> Team:
    """
    Create a new team in the database.

    Args:
        db: SQLAlchemy database session
        team_name: Name of the team (used for imports/mapping)
        display_name: Display name of the team (optional, defaults to team_name)

    Returns:
        The created Team instance
    """
    team = Team(name=team_name, display_name=display_name or team_name)
    db.add(team)
    with transaction(db, refresh=[team]):
        pass
    return team


def get_team_by_name(db: Session, team_name: str) -> Team | None:
    """
    Get a team by its name.

    Args:
        db: SQLAlchemy database session
        team_name: Name of the team to find

    Returns:
        Team instance if found, None otherwise
    """
    return db.query(Team).filter(Team.name == team_name).first()


def get_team_by_id(db: Session, team_id: int) -> Team | None:
    """
    Get a team by its ID.

    Args:
        db: SQLAlchemy database session
        team_id: ID of the team to find

    Returns:
        Team instance if found, None otherwise
    """
    return db.query(Team).filter(Team.id == team_id).first()


def get_all_teams(db: Session) -> list[Team]:
    """
    Get all teams in the database.

    Args:
        db: SQLAlchemy database session

    Returns:
        List of all Team instances
    """
    return db.query(Team).all()


def update_team(db: Session, team_id: int, name: str | None = None, display_name: str | None = None) -> Team | None:
    """
    Update a team's information.

    Args:
        db: SQLAlchemy database session
        team_id: ID of the team to update
        name: New name for the team (optional)
        display_name: New display name for the team (optional)

    Returns:
        Updated Team instance if found, None otherwise
    """
    team = get_team_by_id(db, team_id)
    if team:
        if name is not None:
            team.name = name
        if display_name is not None:
            team.display_name = display_name
        with transaction(db, refresh=[team]):
            pass
    return team
