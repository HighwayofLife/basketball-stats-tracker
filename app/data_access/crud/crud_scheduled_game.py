"""CRUD operations for scheduled games."""

from datetime import date, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

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
        scheduled_game = ScheduledGame(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            season_id=season_id,
            location=location,
            notes=notes,
            status=ScheduledGameStatus.SCHEDULED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(scheduled_game)
        db.commit()
        db.refresh(scheduled_game)
        return scheduled_game

    def get_by_id(self, db: Session, scheduled_game_id: int) -> ScheduledGame | None:
        """Get a scheduled game by ID."""
        return (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(ScheduledGame.id == scheduled_game_id, ScheduledGame.is_deleted == False)
            .first()
        )

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[ScheduledGame]:
        """Get all scheduled games."""
        return (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(ScheduledGame.is_deleted == False)
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
                ScheduledGame.is_deleted == False,
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
            .filter(ScheduledGame.is_deleted == False, ScheduledGame.status == status)
            .order_by(ScheduledGame.scheduled_date.desc())
            .all()
        )

    def find_matching_game(
        self, db: Session, game_date: date, team1_name: str, team2_name: str
    ) -> ScheduledGame | None:
        """Find a scheduled game that matches the given date and teams (regardless of home/away order)."""
        return (
            db.query(ScheduledGame)
            .options(joinedload(ScheduledGame.home_team), joinedload(ScheduledGame.away_team))
            .filter(
                ScheduledGame.scheduled_date == game_date,
                ScheduledGame.status == ScheduledGameStatus.SCHEDULED,
                ScheduledGame.is_deleted == False,
                or_(
                    and_(
                        ScheduledGame.home_team.has(Team.name == team1_name),
                        ScheduledGame.away_team.has(Team.name == team2_name),
                    ),
                    and_(
                        ScheduledGame.home_team.has(Team.name == team2_name),
                        ScheduledGame.away_team.has(Team.name == team1_name),
                    ),
                ),
            )
            .first()
        )

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

        for field, value in updates.items():
            if hasattr(scheduled_game, field):
                setattr(scheduled_game, field, value)

        db.commit()
        db.refresh(scheduled_game)
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

        db.commit()
        return True


crud_scheduled_game = CRUDScheduledGame()
