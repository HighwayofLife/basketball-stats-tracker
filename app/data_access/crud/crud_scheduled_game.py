"""CRUD operations for scheduled games."""

from datetime import date, datetime, time

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.data_access.transaction import transaction
from app.data_access.models import ScheduledGame, ScheduledGameStatus, Team


class CRUDScheduledGame:
    """CRUD operations for scheduled games."""

    def create(
        self,
        db: Session,
        home_team_id: int,
        away_team_id: int,
        scheduled_date: date,
        scheduled_time: str | None = None,
        season_id: int | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> ScheduledGame:
        """Create a new scheduled game."""
        # Convert string time to time object if needed
        if scheduled_time and isinstance(scheduled_time, str):
            hour, minute = map(int, scheduled_time.split(":"))
            scheduled_time_obj = time(hour, minute)
        else:
            scheduled_time_obj = scheduled_time

        scheduled_game = ScheduledGame(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time_obj,
            season_id=season_id,
            location=location,
            notes=notes,
            status=ScheduledGameStatus.SCHEDULED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(scheduled_game)
        with transaction(db, refresh=[scheduled_game]):
            pass
        return scheduled_game

    def get_by_id(self, db: Session, scheduled_game_id: int) -> ScheduledGame | None:
        """Get a scheduled game by ID."""
        return (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(ScheduledGame.id == scheduled_game_id, ScheduledGame.is_deleted.is_not(True))
            .first()
        )

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[ScheduledGame]:
        """Get all scheduled games."""
        return (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(ScheduledGame.is_deleted.is_not(True))
            .order_by(ScheduledGame.scheduled_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_upcoming(self, db: Session, limit: int | None = None) -> list[ScheduledGame]:
        """Get upcoming scheduled games."""
        query = (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(
                ScheduledGame.is_deleted.is_not(True),
                ScheduledGame.status == ScheduledGameStatus.SCHEDULED,
                ScheduledGame.scheduled_date >= date.today(),
            )
            .order_by(ScheduledGame.scheduled_date, ScheduledGame.scheduled_time)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_status(self, db: Session, status: ScheduledGameStatus) -> list[ScheduledGame]:
        """Get scheduled games by status."""
        return (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(ScheduledGame.is_deleted.is_not(True), ScheduledGame.status == status)
            .order_by(ScheduledGame.scheduled_date.desc())
            .all()
        )

    def find_matching_game_by_ids(
        self, db: Session, game_date: date, team1_id: int, team2_id: int
    ) -> ScheduledGame | None:
        """Find a scheduled game that matches the given date and team IDs (regardless of home/away order)."""
        return (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(
                ScheduledGame.scheduled_date == game_date,
                ScheduledGame.status == ScheduledGameStatus.SCHEDULED,
                ScheduledGame.is_deleted.is_not(True),
                or_(
                    and_(
                        ScheduledGame.home_team_id == team1_id,
                        ScheduledGame.away_team_id == team2_id,
                    ),
                    and_(
                        ScheduledGame.home_team_id == team2_id,
                        ScheduledGame.away_team_id == team1_id,
                    ),
                ),
            )
            .first()
        )

    def find_matching_game(
        self, db: Session, game_date: date, team1_name: str, team2_name: str
    ) -> ScheduledGame | None:
        """Find a scheduled game that matches the given date and teams (regardless of home/away order).

        First tries to match using Team.name, then falls back to Team.display_name for more flexible matching.
        """
        # First, try matching with Team.name (primary matching for CSV imports)
        query_base = (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(
                ScheduledGame.scheduled_date == game_date,
                ScheduledGame.status == ScheduledGameStatus.SCHEDULED,
                ScheduledGame.is_deleted.is_not(True),
            )
        )

        # Try exact match with Team.name first
        result = query_base.filter(
            or_(
                and_(
                    ScheduledGame.home_team.has(Team.name == team1_name),
                    ScheduledGame.away_team.has(Team.name == team2_name),
                ),
                and_(
                    ScheduledGame.home_team.has(Team.name == team2_name),
                    ScheduledGame.away_team.has(Team.name == team1_name),
                ),
            )
        ).first()

        if result:
            return result

        # If no match found with Team.name, try matching with Team.display_name as fallback
        return query_base.filter(
            or_(
                and_(
                    ScheduledGame.home_team.has(Team.display_name == team1_name),
                    ScheduledGame.away_team.has(Team.display_name == team2_name),
                ),
                and_(
                    ScheduledGame.home_team.has(Team.display_name == team2_name),
                    ScheduledGame.away_team.has(Team.display_name == team1_name),
                ),
            )
        ).first()

    def update(
        self,
        db: Session,
        scheduled_game_id: int,
        **updates,
    ) -> ScheduledGame | None:
        """Update a scheduled game."""
        scheduled_game = self.get_by_id(db, scheduled_game_id)
        if not scheduled_game:
            return None

        updates["updated_at"] = datetime.utcnow()

        # Convert string time to time object if needed
        if "scheduled_time" in updates and updates["scheduled_time"] and isinstance(updates["scheduled_time"], str):
            hour, minute = map(int, updates["scheduled_time"].split(":"))
            updates["scheduled_time"] = time(hour, minute)

        for field, value in updates.items():
            if hasattr(scheduled_game, field):
                setattr(scheduled_game, field, value)

        with transaction(db, refresh=[scheduled_game]):
            pass
        return scheduled_game

    def mark_completed(self, db: Session, scheduled_game_id: int, game_id: int) -> ScheduledGame | None:
        """Mark a scheduled game as completed and link it to the actual game."""
        return self.update(
            db,
            scheduled_game_id,
            status=ScheduledGameStatus.COMPLETED,
            game_id=game_id,
        )

    def cancel(self, db: Session, scheduled_game_id: int) -> ScheduledGame | None:
        """Cancel a scheduled game."""
        return self.update(db, scheduled_game_id, status=ScheduledGameStatus.CANCELLED)

    def delete(self, db: Session, scheduled_game_id: int) -> bool:
        """Soft delete a scheduled game."""
        scheduled_game = self.get_by_id(db, scheduled_game_id)
        if not scheduled_game:
            return False

        scheduled_game.is_deleted = True
        scheduled_game.deleted_at = datetime.utcnow()
        scheduled_game.updated_at = datetime.utcnow()

        with transaction(db):
            pass
        return True


crud_scheduled_game = CRUDScheduledGame()
