"""CRUD operations for Season model."""

from datetime import date, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.data_access.models import Game, Season


class SeasonCRUD:
    """CRUD operations for Season model."""

    def __init__(self, db_session: Session):
        """Initialize Season CRUD with database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session

    def create(
        self,
        name: str,
        code: str,
        start_date: date,
        end_date: date,
        description: str | None = None,
        is_active: bool = False,
    ) -> Season:
        """Create a new season.

        Args:
            name: Season name (e.g., "Spring 2025")
            code: Unique season code (e.g., "2025-spring")
            start_date: Season start date
            end_date: Season end date
            description: Optional season description
            is_active: Whether this is the active season

        Returns:
            Created Season object
        """
        # If setting as active, deactivate all other seasons
        if is_active:
            self.db_session.query(Season).update({"is_active": False})

        season = Season(
            name=name,
            code=code,
            start_date=start_date,
            end_date=end_date,
            description=description,
            is_active=is_active,
        )
        self.db_session.add(season)
        self.db_session.commit()
        self.db_session.refresh(season)
        return season

    def get_by_id(self, season_id: int) -> Season | None:
        """Get a season by ID.

        Args:
            season_id: Season ID

        Returns:
            Season object if found, None otherwise
        """
        return self.db_session.query(Season).filter(Season.id == season_id).first()

    def get_by_code(self, code: str) -> Season | None:
        """Get a season by code.

        Args:
            code: Season code

        Returns:
            Season object if found, None otherwise
        """
        return self.db_session.query(Season).filter(Season.code == code).first()

    def get_active_season(self) -> Season | None:
        """Get the currently active season.

        Returns:
            Active Season object if found, None otherwise
        """
        return self.db_session.query(Season).filter(Season.is_active).first()

    def get_season_for_date(self, game_date: date) -> Season | None:
        """Get the season that contains a specific date.

        Args:
            game_date: Date to check

        Returns:
            Season object if found, None otherwise
        """
        return (
            self.db_session.query(Season)
            .filter(and_(Season.start_date <= game_date, Season.end_date >= game_date))
            .first()
        )

    def list_seasons(self, include_inactive: bool = True) -> list[Season]:
        """List all seasons.

        Args:
            include_inactive: Whether to include inactive seasons

        Returns:
            List of Season objects
        """
        query = self.db_session.query(Season)
        if not include_inactive:
            query = query.filter(Season.is_active)
        return query.order_by(Season.start_date.desc()).all()

    def update(
        self,
        season_id: int,
        name: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> Season | None:
        """Update a season.

        Args:
            season_id: Season ID
            name: New season name
            start_date: New start date
            end_date: New end date
            description: New description
            is_active: New active status

        Returns:
            Updated Season object if found, None otherwise
        """
        season = self.get_by_id(season_id)
        if not season:
            return None

        if name is not None:
            season.name = name
        if start_date is not None:
            season.start_date = start_date
        if end_date is not None:
            season.end_date = end_date
        if description is not None:
            season.description = description
        if is_active is not None:
            # If setting as active, deactivate all other seasons
            if is_active:
                self.db_session.query(Season).filter(Season.id != season_id).update({"is_active": False})
            season.is_active = is_active

        season.updated_at = datetime.utcnow()
        self.db_session.commit()
        self.db_session.refresh(season)
        return season

    def set_active_season(self, season_id: int) -> Season | None:
        """Set a season as the active season.

        Args:
            season_id: Season ID

        Returns:
            Updated Season object if found, None otherwise
        """
        return self.update(season_id, is_active=True)

    def delete(self, season_id: int) -> bool:
        """Delete a season.

        Note: Will only delete if no games are associated with the season.

        Args:
            season_id: Season ID

        Returns:
            True if deleted, False otherwise
        """
        season = self.get_by_id(season_id)
        if not season:
            return False

        # Check if any games are associated with this season
        game_count = self.db_session.query(Game).filter(Game.season_id == season_id).count()
        if game_count > 0:
            return False

        self.db_session.delete(season)
        self.db_session.commit()
        return True

    def get_season_game_count(self, season_id: int) -> int:
        """Get the number of games in a season.

        Args:
            season_id: Season ID

        Returns:
            Number of games in the season
        """
        return self.db_session.query(Game).filter(Game.season_id == season_id).count()

    def check_overlapping_seasons(self, start_date: date, end_date: date, exclude_id: int | None = None) -> bool:
        """Check if a date range overlaps with existing seasons.

        Args:
            start_date: Start date to check
            end_date: End date to check
            exclude_id: Season ID to exclude from check (for updates)

        Returns:
            True if overlapping seasons exist, False otherwise
        """
        query = self.db_session.query(Season).filter(
            or_(
                and_(Season.start_date <= start_date, Season.end_date >= start_date),
                and_(Season.start_date <= end_date, Season.end_date >= end_date),
                and_(Season.start_date >= start_date, Season.end_date <= end_date),
            )
        )

        if exclude_id:
            query = query.filter(Season.id != exclude_id)

        return query.count() > 0
