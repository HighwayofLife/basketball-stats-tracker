# app/data_access/models_awards.py

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.models import Base

if TYPE_CHECKING:
    from app.data_access.models import Player


class PlayerAward(Base):
    """Model for tracking player awards by season and type."""

    __tablename__ = "player_awards"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "2024"
    award_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "player_of_the_week"
    week_date: Mapped[date] = mapped_column(Date, nullable=False)  # Week start date
    points_scored: Mapped[int | None] = mapped_column(Integer, nullable=True)  # For reference
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="awards")

    # Unique constraint to prevent duplicate awards for same week
    __table_args__ = (UniqueConstraint("award_type", "week_date", "season", name="unique_weekly_award"),)

    def __repr__(self) -> str:
        return (
            f"<PlayerAward(player_id={self.player_id}, type='{self.award_type}', "
            f"season='{self.season}', week='{self.week_date}')>"
        )
