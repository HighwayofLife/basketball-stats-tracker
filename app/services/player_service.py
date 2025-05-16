"""
Service for player-related operations.
"""

from sqlalchemy.orm import Session

from app.data_access.crud import create_player, get_player_by_id, get_player_by_team_and_jersey, get_players_by_team
from app.data_access.models import Player


class PlayerService:
    """
    Service class for player-related operations.
    """

    def __init__(self, db_session: Session):
        """
        Initialize the PlayerService with a database session.

        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db = db_session

    def get_or_create_player(self, team_id: int, jersey_number: int, player_name: str | None = None) -> Player:
        """
        Get a player by team and jersey number, or create if not found.

        Args:
            team_id: ID of the team the player belongs to
            jersey_number: Player's jersey number
            player_name: Player's name (required for creation, optional for lookup)

        Returns:
            The retrieved or created Player instance

        Raises:
            ValueError: If player doesn't exist and name isn't provided for creation
        """
        # Try to find the player by team and jersey
        player = get_player_by_team_and_jersey(self.db, team_id, jersey_number)

        if player is None:
            # If player doesn't exist, we need a name to create them
            if player_name is None or player_name.strip() == "":
                raise ValueError(
                  f"Player with jersey number {jersey_number} doesn't exist "
                  f"on team {team_id}, and no name was provided for creation."
                )

            # Create the player
            player = create_player(self.db, player_name, jersey_number, team_id)

        # If the player exists but the name was provided and differs, we could update
        # the name here if that's desired behavior.

        return player

    def get_player_details(self, player_id: int) -> Player | None:
        """
        Get detailed information about a player.

        Args:
            player_id: ID of the player

        Returns:
            The Player instance if found, None otherwise
        """
        return get_player_by_id(self.db, player_id)

    def get_team_roster(self, team_id: int) -> list[Player]:
        """
        Get the roster of all players for a team.

        Args:
            team_id: ID of the team

        Returns:
            List of Player instances
        """
        return get_players_by_team(self.db, team_id)
