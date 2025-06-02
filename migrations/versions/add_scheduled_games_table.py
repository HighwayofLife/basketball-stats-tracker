"""add_scheduled_games_table

Revision ID: add_scheduled_games_001
Revises: 87de4895a505
Create Date: 2025-06-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_scheduled_games_001"
down_revision: str | None = "87de4895a505"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create scheduled_games table
    op.create_table(
        "scheduled_games",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("SCHEDULED", "COMPLETED", "CANCELLED", "POSTPONED", name="scheduledgamestatus"),
            nullable=False,
        ),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, default=sa.func.current_timestamp()),
        sa.CheckConstraint("home_team_id != away_team_id", name="check_different_teams"),
        sa.UniqueConstraint("scheduled_date", "home_team_id", "away_team_id", name="uq_scheduled_game_date_teams"),
    )

    # Create indexes
    op.create_index("idx_scheduled_games_date_status", "scheduled_games", ["scheduled_date", "status"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_scheduled_games_date_status", table_name="scheduled_games")

    # Drop table
    op.drop_table("scheduled_games")
