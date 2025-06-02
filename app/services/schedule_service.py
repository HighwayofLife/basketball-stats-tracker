"""Service for managing scheduled games."""

from datetime import date, time

from sqlalchemy.orm import Session

from app.data_access.crud.crud_scheduled_game import crud_scheduled_game
from app.data_access.models import ScheduledGame, ScheduledGameStatus


class ScheduleService:
    """Service for managing scheduled games."""

    def create_scheduled_game(
        self,
        db: Session,
        home_team_id: int,
        away_team_id: int,
        scheduled_date: date,
        scheduled_time: time | None = None,
        season_id: int | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> ScheduledGame:
        """Create a new scheduled game."""
        if home_team_id == away_team_id:
            raise ValueError("Home team and away team cannot be the same")

        # Check if a game already exists for these teams on this date
        existing_game = crud_scheduled_game.find_matching_game(db, scheduled_date, home_team_id, away_team_id)
        if existing_game:
            raise ValueError(f"A scheduled game already exists between these teams on {scheduled_date}")

        return crud_scheduled_game.create(
            db=db,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            season_id=season_id,
            location=location,
            notes=notes,
        )

    def get_scheduled_game(self, db: Session, scheduled_game_id: int) -> ScheduledGame | None:
        """Get a scheduled game by ID."""
        return crud_scheduled_game.get_by_id(db, scheduled_game_id)

    def get_all_scheduled_games(self, db: Session, skip: int = 0, limit: int = 100) -> list[ScheduledGame]:
        """Get all scheduled games."""
        return crud_scheduled_game.get_all(db, skip=skip, limit=limit)

    def get_upcoming_games(self, db: Session, limit: int | None = None) -> list[ScheduledGame]:
        """Get upcoming scheduled games."""
        return crud_scheduled_game.get_upcoming(db, limit=limit)

    def get_next_games(self, db: Session, count: int = 3) -> list[ScheduledGame]:
        """Get the next N upcoming games."""
        return crud_scheduled_game.get_upcoming(db, limit=count)

    def get_games_by_status(self, db: Session, status: ScheduledGameStatus) -> list[ScheduledGame]:
        """Get scheduled games by status."""
        return crud_scheduled_game.get_by_status(db, status)

    def update_scheduled_game(
        self,
        db: Session,
        scheduled_game_id: int,
        **updates,
    ) -> ScheduledGame | None:
        """Update a scheduled game."""
        return crud_scheduled_game.update(db, scheduled_game_id, **updates)

    def cancel_scheduled_game(self, db: Session, scheduled_game_id: int) -> ScheduledGame | None:
        """Cancel a scheduled game."""
        return crud_scheduled_game.cancel(db, scheduled_game_id)

    def link_game_to_schedule(self, db: Session, scheduled_game_id: int, game_id: int) -> ScheduledGame | None:
        """Link a completed game to its scheduled game entry."""
        return crud_scheduled_game.mark_completed(db, scheduled_game_id, game_id)

    def find_matching_scheduled_game(
        self, db: Session, game_date: date, team1_name: str, team2_name: str
    ) -> ScheduledGame | None:
        """
        Find a scheduled game that matches the given date and teams.

        This is used during CSV import to automatically match games with their schedule.
        The teams can be in any order (home/away doesn't matter for matching).
        """
        return crud_scheduled_game.find_matching_game(db, game_date, team1_name, team2_name)

    def delete_scheduled_game(self, db: Session, scheduled_game_id: int) -> bool:
        """Delete a scheduled game (soft delete)."""
        return crud_scheduled_game.delete(db, scheduled_game_id)


schedule_service = ScheduleService()
