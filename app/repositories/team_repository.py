"""Repository for team-related database operations."""


from sqlalchemy.orm import Session

from app.data_access.models import Game, Player, Team

from .base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for team operations."""

    def __init__(self, session: Session):
        """Initialize the team repository.

        Args:
            session: The database session
        """
        super().__init__(Team, session)

    def get_with_player_count(self) -> list[dict]:
        """Get all teams with their active player counts.

        Returns:
            List of dictionaries with team info and player count
        """
        teams = self.session.query(Team).all()
        result = []

        for team in teams:
            player_count = (
                self.session.query(Player).filter(Player.team_id == team.id, Player.is_active == True).count()
            )
            result.append({"id": team.id, "name": team.name, "player_count": player_count})

        return result

    def get_by_name(self, name: str) -> Team | None:
        """Get a team by name.

        Args:
            name: The team name

        Returns:
            The team or None if not found
        """
        return self.session.query(Team).filter(Team.name == name).first()

    def has_games(self, team_id: int) -> bool:
        """Check if a team has any games.

        Args:
            team_id: The team ID

        Returns:
            True if the team has games, False otherwise
        """
        games_count = (
            self.session.query(Game)
            .filter((Game.playing_team_id == team_id) | (Game.opponent_team_id == team_id))
            .count()
        )
        return games_count > 0

    def get_deleted_teams(self) -> list[Team]:
        """Get all soft-deleted teams.

        Returns:
            List of deleted teams
        """
        return self.session.query(Team).filter(Team.is_deleted == True).order_by(Team.deleted_at.desc()).all()
