"""Repository for player-related database operations."""

from sqlalchemy.orm import Session

from app.data_access.models import Player, PlayerGameStats, Team

from .base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    """Repository for player operations."""

    def __init__(self, session: Session):
        """Initialize the player repository.

        Args:
            session: The database session
        """
        super().__init__(Player, session)

    def get_with_team(self, player_id: int) -> Player | None:
        """Get a player with their team information.

        Args:
            player_id: The player ID

        Returns:
            The player with team info or None if not found
        """
        return self.session.query(Player).filter(Player.id == player_id).first()

    def get_players_with_teams(self, team_id: int | None = None, active_only: bool = True) -> list[tuple[Player, Team]]:
        """Get players with their team information.

        Args:
            team_id: Optional team ID filter
            active_only: Whether to only include active players

        Returns:
            List of (player, team) tuples
        """
        query = self.session.query(Player, Team).join(Team, Player.team_id == Team.id)

        if team_id:
            query = query.filter(Player.team_id == team_id)

        if active_only:
            query = query.filter(Player.is_active)

        return query.order_by(Team.name, Player.jersey_number).all()  # type: ignore[return-value]

    def get_by_jersey_number(self, team_id: int, jersey_number: int) -> Player | None:
        """Get a player by team and jersey number.

        Args:
            team_id: The team ID
            jersey_number: The jersey number

        Returns:
            The player or None if not found
        """
        return (
            self.session.query(Player)
            .filter(
                Player.team_id == team_id,
                Player.jersey_number == jersey_number,
                Player.is_active,
            )
            .first()
        )

    def has_game_stats(self, player_id: int) -> bool:
        """Check if a player has any game statistics.

        Args:
            player_id: The player ID

        Returns:
            True if the player has game stats, False otherwise
        """
        stats_count = self.session.query(PlayerGameStats).filter(PlayerGameStats.player_id == player_id).count()
        return stats_count > 0

    def get_team_players(self, team_id: int, active_only: bool = True) -> list[Player]:
        """Get all players for a team.

        Args:
            team_id: The team ID
            active_only: Whether to only include active players

        Returns:
            List of players
        """
        query = self.session.query(Player).filter(Player.team_id == team_id)

        if active_only:
            query = query.filter(Player.is_active)

        return query.order_by(Player.jersey_number).all()

    def get_deleted_players(self) -> list[Player]:
        """Get all soft-deleted players.

        Returns:
            List of deleted players
        """
        return self.session.query(Player).filter(Player.is_deleted).order_by(Player.deleted_at.desc()).all()

    def deactivate(self, player_id: int) -> bool:
        """Deactivate a player instead of deleting.

        Args:
            player_id: The player ID

        Returns:
            True if deactivated, False if not found
        """
        player = self.get_by_id(player_id)
        if player:
            player.is_active = False
            self.session.commit()
            return True
        return False
