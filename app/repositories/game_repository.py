"""Repository for game-related database operations."""

from datetime import date

from sqlalchemy.orm import Session

from app.data_access.models import Game

from .base import BaseRepository


class GameRepository(BaseRepository[Game]):
    """Repository for game operations."""

    def __init__(self, session: Session):
        """Initialize the game repository.

        Args:
            session: The database session
        """
        super().__init__(Game, session)

    def get_games_with_teams(self, limit: int = 20, offset: int = 0, team_id: int | None = None) -> list[Game]:
        """Get games with team information.

        Args:
            limit: Maximum number of games to return
            offset: Number of games to skip
            team_id: Optional team ID filter

        Returns:
            List of games with teams loaded
        """
        query = self.session.query(Game)

        if team_id is not None:
            query = query.filter((Game.playing_team_id == team_id) | (Game.opponent_team_id == team_id))

        return query.order_by(Game.date.desc()).offset(offset).limit(limit).all()

    def get_by_date_range(self, start_date: date, end_date: date, team_id: int | None = None) -> list[Game]:
        """Get games within a date range.

        Args:
            start_date: Start date
            end_date: End date
            team_id: Optional team ID filter

        Returns:
            List of games
        """
        query = self.session.query(Game).filter(Game.date >= start_date, Game.date <= end_date)

        if team_id:
            query = query.filter((Game.playing_team_id == team_id) | (Game.opponent_team_id == team_id))

        return query.order_by(Game.date).all()

    def get_deleted_games(self) -> list[Game]:
        """Get all soft-deleted games.

        Returns:
            List of deleted games
        """
        return self.session.query(Game).filter(Game.is_deleted == True).order_by(Game.deleted_at.desc()).all()

    def get_recent_games(self, limit: int = 5) -> list[Game]:
        """Get the most recent games.

        Args:
            limit: Number of games to return

        Returns:
            List of recent games
        """
        return self.session.query(Game).order_by(Game.date.desc()).limit(limit).all()
