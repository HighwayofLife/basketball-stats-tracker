"""Add live game entry tables and fields

Revision ID: 13bb0669f405
Revises: ac78b1e94d31
Create Date: 2025-05-22 20:58:51.983162

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "13bb0669f405"
down_revision = "ac78b1e94d31"
branch_labels = None
depends_on = None


def upgrade():
    # Create game_states table
    op.create_table(
        "game_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("current_quarter", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quarter_time_remaining", sa.Integer(), nullable=True),
        sa.Column("is_live", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("home_timeouts_remaining", sa.Integer(), server_default="5"),
        sa.Column("away_timeouts_remaining", sa.Integer(), server_default="5"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("current_quarter >= 1 AND current_quarter <= 4", name="check_quarter_number"),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id"),
    )

    # Create game_events table
    op.create_table(
        "game_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_game_events_game_id", "game_events", ["game_id"], unique=False)
    op.create_index("idx_game_events_timestamp", "game_events", ["timestamp"], unique=False)

    # Create active_rosters table
    op.create_table(
        "active_rosters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("checked_out_at", sa.DateTime(), nullable=True),
        sa.Column("is_starter", sa.Boolean(), server_default="0"),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "player_id"),
    )

    # Add new columns to games table
    op.add_column("games", sa.Column("location", sa.String(length=255), nullable=True))
    op.add_column("games", sa.Column("scheduled_time", sa.Time(), nullable=True))
    op.add_column("games", sa.Column("notes", sa.Text(), nullable=True))

    # Add new columns to players table
    op.add_column("players", sa.Column("position", sa.String(length=10), nullable=True))
    op.add_column("players", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("weight", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("year", sa.String(length=20), nullable=True))
    op.add_column("players", sa.Column("is_active", sa.Boolean(), server_default="1"))


def downgrade():
    # Remove columns from players table
    op.drop_column("players", "is_active")
    op.drop_column("players", "year")
    op.drop_column("players", "weight")
    op.drop_column("players", "height")
    op.drop_column("players", "position")

    # Remove columns from games table
    op.drop_column("games", "notes")
    op.drop_column("games", "scheduled_time")
    op.drop_column("games", "location")

    # Drop tables
    op.drop_table("active_rosters")
    op.drop_index("idx_game_events_timestamp", table_name="game_events")
    op.drop_index("idx_game_events_game_id", table_name="game_events")
    op.drop_table("game_events")
    op.drop_table("game_states")
