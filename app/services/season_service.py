"""Service layer for season management."""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.data_access.crud.crud_season import SeasonCRUD
from app.data_access.models import Game, Season

logger = logging.getLogger(__name__)


class SeasonService:
    """Service for managing seasons."""

    def __init__(self, db_session: Session):
        """Initialize the season service.

        Args:
            db_session: The database session to use
        """
        self.db_session = db_session
        self.season_crud = SeasonCRUD(db_session)

    def create_season(
        self,
        name: str,
        code: str,
        start_date: date,
        end_date: date,
        description: str | None = None,
        set_as_active: bool = False,
    ) -> tuple[bool, str, Season | None]:
        """Create a new season.

        Args:
            name: Season name (e.g., "Spring 2025")
            code: Unique season code (e.g., "2025-spring")
            start_date: Season start date
            end_date: Season end date
            description: Optional season description
            set_as_active: Whether to set this as the active season

        Returns:
            Tuple of (success, message, season)
        """
        try:
            # Validate dates
            if start_date >= end_date:
                return False, "Start date must be before end date", None

            # Check for existing code
            if self.season_crud.get_by_code(code):
                return False, f"Season with code '{code}' already exists", None

            # Check for overlapping seasons
            if self.season_crud.check_overlapping_seasons(start_date, end_date):
                return False, "Season dates overlap with an existing season", None

            # Create the season
            season = self.season_crud.create(
                name=name,
                code=code,
                start_date=start_date,
                end_date=end_date,
                description=description,
                is_active=set_as_active,
            )

            logger.info(f"Created season: {season.name} ({season.code})")
            return True, f"Season '{season.name}' created successfully", season

        except Exception as e:
            logger.error(f"Error creating season: {e}")
            return False, f"Failed to create season: {str(e)}", None

    def update_season(
        self,
        season_id: int,
        name: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        description: str | None = None,
    ) -> tuple[bool, str, Season | None]:
        """Update a season.

        Args:
            season_id: Season ID
            name: New season name
            start_date: New start date
            end_date: New end date
            description: New description

        Returns:
            Tuple of (success, message, season)
        """
        try:
            season = self.season_crud.get_by_id(season_id)
            if not season:
                return False, "Season not found", None

            # Validate dates if provided
            check_start = start_date if start_date else season.start_date
            check_end = end_date if end_date else season.end_date
            if check_start >= check_end:
                return False, "Start date must be before end date", None

            # Check for overlapping seasons if dates changed
            if (start_date or end_date) and self.season_crud.check_overlapping_seasons(
                check_start, check_end, exclude_id=season_id
            ):
                return False, "New dates overlap with an existing season", None

            # Update the season
            season = self.season_crud.update(
                season_id=season_id,
                name=name,
                start_date=start_date,
                end_date=end_date,
                description=description,
            )

            logger.info(f"Updated season: {season.name} ({season.code})")
            return True, f"Season '{season.name}' updated successfully", season

        except Exception as e:
            logger.error(f"Error updating season: {e}")
            return False, f"Failed to update season: {str(e)}", None

    def set_active_season(self, season_id: int) -> tuple[bool, str]:
        """Set a season as the active season.

        Args:
            season_id: Season ID

        Returns:
            Tuple of (success, message)
        """
        try:
            season = self.season_crud.set_active_season(season_id)
            if not season:
                return False, "Season not found"

            logger.info(f"Set active season: {season.name} ({season.code})")
            return True, f"Season '{season.name}' is now active"

        except Exception as e:
            logger.error(f"Error setting active season: {e}")
            return False, f"Failed to set active season: {str(e)}"

    def delete_season(self, season_id: int) -> tuple[bool, str]:
        """Delete a season.

        Args:
            season_id: Season ID

        Returns:
            Tuple of (success, message)
        """
        try:
            season = self.season_crud.get_by_id(season_id)
            if not season:
                return False, "Season not found"

            # Check if season has games
            game_count = self.season_crud.get_season_game_count(season_id)
            if game_count > 0:
                return False, f"Cannot delete season with {game_count} games. Remove games first."

            if self.season_crud.delete(season_id):
                logger.info(f"Deleted season: {season.name} ({season.code})")
                return True, f"Season '{season.name}' deleted successfully"
            else:
                return False, "Failed to delete season"

        except Exception as e:
            logger.error(f"Error deleting season: {e}")
            return False, f"Failed to delete season: {str(e)}"

    def get_active_season(self) -> Season | None:
        """Get the currently active season.

        Returns:
            Active Season object if found, None otherwise
        """
        return self.season_crud.get_active_season()

    def get_season_for_date(self, game_date: date) -> Season | None:
        """Get the season that contains a specific date.

        Args:
            game_date: Date to check

        Returns:
            Season object if found, None otherwise
        """
        return self.season_crud.get_season_for_date(game_date)

    def list_seasons(self, include_inactive: bool = True) -> list[dict]:
        """List all seasons with game counts.

        Args:
            include_inactive: Whether to include inactive seasons

        Returns:
            List of season dictionaries with game counts
        """
        seasons = self.season_crud.list_seasons(include_inactive)
        result = []

        for season in seasons:
            game_count = self.season_crud.get_season_game_count(season.id)
            result.append(
                {
                    "id": season.id,
                    "name": season.name,
                    "code": season.code,
                    "start_date": season.start_date.isoformat(),
                    "end_date": season.end_date.isoformat(),
                    "is_active": season.is_active,
                    "description": season.description,
                    "game_count": game_count,
                }
            )

        return result

    def migrate_existing_games(self) -> tuple[bool, str]:
        """Migrate existing games to seasons based on their dates.

        This will:
        1. Create seasons for existing "YYYY-YYYY" season strings
        2. Assign games to appropriate seasons based on dates

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get all unique season strings from PlayerSeasonStats and TeamSeasonStats
            from app.data_access.models import PlayerSeasonStats, TeamSeasonStats

            player_seasons = self.db_session.query(PlayerSeasonStats.season).distinct().all()
            team_seasons = self.db_session.query(TeamSeasonStats.season).distinct().all()

            # Combine and deduplicate
            season_strings = set()
            for (season_str,) in player_seasons:
                if season_str:
                    season_strings.add(season_str)
            for (season_str,) in team_seasons:
                if season_str:
                    season_strings.add(season_str)

            created_seasons = []

            # Create Season records for each unique season string
            for season_str in sorted(season_strings):
                # Parse "YYYY-YYYY" format
                try:
                    start_year, end_year = season_str.split("-")
                    start_year = int(start_year)
                    end_year = int(end_year)

                    # Traditional basketball season: October to April
                    start_date = date(start_year, 10, 1)
                    end_date = date(end_year, 4, 30)

                    # Create season if it doesn't exist
                    existing = self.season_crud.get_by_code(season_str)
                    if not existing:
                        season = self.season_crud.create(
                            name=f"Season {season_str}",
                            code=season_str,
                            start_date=start_date,
                            end_date=end_date,
                            description=f"Migrated from {season_str} season data",
                            is_active=False,
                        )
                        created_seasons.append(season)
                        logger.info(f"Created season from migration: {season.name}")
                except Exception as e:
                    logger.warning(f"Failed to parse season string '{season_str}': {e}")
                    continue

            # Assign games to seasons based on their dates
            games_without_season = self.db_session.query(Game).filter(Game.season_id.is_(None)).all()

            games_updated = 0
            for game in games_without_season:
                season = self.season_crud.get_season_for_date(game.date)
                if season:
                    game.season_id = season.id
                    games_updated += 1

            self.db_session.commit()

            message = f"Migration complete: Created {len(created_seasons)} seasons, updated {games_updated} games"
            logger.info(message)
            return True, message

        except Exception as e:
            logger.error(f"Error migrating games to seasons: {e}")
            self.db_session.rollback()
            return False, f"Migration failed: {str(e)}"
