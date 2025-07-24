"""Add PlayerAward table for detailed award tracking

Revision ID: e0473a26cb0b
Revises: 7e567a4a5d6e
Create Date: 2025-07-23 18:11:39.130164

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e0473a26cb0b"
down_revision = "3d65696eeb09"
branch_labels = None
depends_on = None


def upgrade():
    # Create player_awards table for detailed award tracking
    op.create_table(
        "player_awards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("award_type", sa.String(length=50), nullable=False),
        sa.Column("week_date", sa.Date(), nullable=False),
        sa.Column("points_scored", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("award_type", "week_date", "season", name="unique_weekly_award"),
    )


def downgrade():
    # Drop player_awards table
    op.drop_table("player_awards")
