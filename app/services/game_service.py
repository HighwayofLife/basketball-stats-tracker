"""
Service for game-related operations.
"""

from sqlalchemy.orm import Session

from app.data_access.crud import (
    create_game,
    create_team,
    get_all_teams,
    get_team_by_name,
)
from app.data_access.models import Game, Team


class GameService:
    """
    Service class for game-related operations, including team management.
    """

    def __init__(self, db_session: Session):
        """
        Initialize the GameService with a database session.

        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db = db_session

    def add_game(self, date: str, playing_team_name: str, opponent_team_name: str) -> Game:
        """
        Add a new game to the database, creating teams if they don't already exist.

        Args:
            date: Date of the game in YYYY-MM-DD format
            playing_team_name: Name of the home/playing team
            opponent_team_name: Name of the away/opponent team

        Returns:
            The created Game instance
        """
        # Get or create both teams
        playing_team = self.get_or_create_team(playing_team_name)
        opponent_team = self.get_or_create_team(opponent_team_name)

        # Create the game
        return create_game(self.db, date, playing_team.id, opponent_team.id)

    def get_or_create_team(self, team_name: str) -> Team:
        """
        Get a team by name, or create it if it doesn't exist.

        Args:
            team_name: Name of the team to get or create

        Returns:
            The retrieved or created Team instance
        """
        team = get_team_by_name(self.db, team_name)
        if team is None:
            team = create_team(self.db, team_name)
        return team

    def list_all_teams(self) -> list[Team]:
        """
        Get a list of all teams in the database.

        Returns:
            List of all Team instances
        """
        return get_all_teams(self.db)
