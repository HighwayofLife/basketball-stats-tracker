"""
CRUD operations for Team model.
"""

from sqlalchemy.orm import Session

from app.data_access.models import Team


def create_team(db: Session, team_name: str) -> Team:
    """
    Create a new team in the database.

    Args:
        db: SQLAlchemy database session
        team_name: Name of the team

    Returns:
        The created Team instance
    """
    team = Team(name=team_name)
    db.add(team)
    db.commit()
    db.refresh(team)
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
