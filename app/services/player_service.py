"""
Service for player-related operations.
"""

from sqlalchemy.orm import Session

from app.data_access.crud import create_player, get_player_by_id, get_player_by_team_and_jersey, get_players_by_team
from app.data_access.models import Player, Team


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
        self._db_session = db_session

    def get_or_create_player(self, team_id: int, jersey_number: str, player_name: str | None = None) -> Player:
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
        player = get_player_by_team_and_jersey(self._db_session, team_id, jersey_number)

        if player is None:
            # If player doesn't exist, we need a name to create them
            if player_name is None or player_name.strip() == "":
                raise ValueError(
                    f"Player with jersey number {jersey_number} doesn't exist "
                    f"on team {team_id}, and no name was provided for creation."
                )

            # Create the player
            player = create_player(self._db_session, player_name, jersey_number, team_id)

        # If the player exists but the name was provided and differs, update the name
        if player is not None and player_name and player.name != player_name:
            player.name = player_name
            self._db_session.commit()

        return player

    def get_or_create_substitute_player(self, jersey_number: str, player_name: str | None = None) -> Player | None:
        """
        Get or create a substitute player.

        Substitute players belong to a special "Guest Players" team and can play
        for any team in individual games.

        Args:
            jersey_number: Player's jersey number
            player_name: Player's name (defaults to "Sub #{jersey_number}" if not provided)

        Returns:
            The retrieved or created substitute Player instance
        """
        from app.data_access.crud.crud_team import get_team_by_name

        # Get or create the Guest Players team
        guest_team = get_team_by_name(self._db_session, "Guest Players")
        if not guest_team:
            # Create the Guest Players team if it doesn't exist
            guest_team = self._db_session.query(Team).filter_by(name="Guest Players").first()
            if not guest_team:
                guest_team = Team(name="Guest Players", display_name="Guest Players")
                self._db_session.add(guest_team)
                self._db_session.commit()

        # Default name if not provided
        if not player_name or player_name.strip().lower() in ["unknown", ""]:
            player_name = f"Sub #{jersey_number}"

        # Try to find existing substitute player with this jersey number
        player = (
            self._db_session.query(Player)
            .filter_by(team_id=guest_team.id, jersey_number=jersey_number, is_substitute=True)
            .first()
        )

        if not player:
            # Create new substitute player
            player = Player(team_id=guest_team.id, name=player_name, jersey_number=jersey_number, is_substitute=True)
            self._db_session.add(player)
            self._db_session.commit()
        elif player.name != player_name and player_name != f"Sub #{jersey_number}":
            # Update name if it's different and not the default
            player.name = player_name
            self._db_session.commit()

        return player

    def get_player_details(self, player_id: int) -> Player | None:
        """
        Get detailed information about a player.

        Args:
            player_id: ID of the player

        Returns:
            The Player instance if found, None otherwise
        """
        return get_player_by_id(self._db_session, player_id)

    def get_team_roster(self, team_id: int) -> list[Player]:
        """
        Get the roster of all players for a team.

        Args:
            team_id: ID of the team

        Returns:
            List of Player instances
        """
        return get_players_by_team(self._db_session, team_id)
