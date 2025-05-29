"""add_substitute_player_support

Revision ID: b1e1ff107303
Revises: a6e40a9168f7
Create Date: 2025-05-29 09:26:54.181459

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b1e1ff107303"
down_revision = "a6e40a9168f7"
branch_labels = None
depends_on = None


def upgrade():
    # Add is_substitute flag to players table
    op.add_column("players", sa.Column("is_substitute", sa.Boolean(), nullable=False, server_default="false"))

    # Add playing_for_team_id to player_game_stats to track which team a substitute played for
    op.add_column("player_game_stats", sa.Column("playing_for_team_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_player_game_stats_playing_for_team", "player_game_stats", "teams", ["playing_for_team_id"], ["id"]
    )

    # Add is_substitute flag to active_rosters
    op.add_column("active_rosters", sa.Column("is_substitute", sa.Boolean(), nullable=False, server_default="false"))

    # Create a unique index for substitute player identification
    op.create_index(
        "ix_players_substitute_identifier",
        "players",
        ["name", "jersey_number"],
        unique=True,
        postgresql_where=sa.text("is_substitute = true"),
    )


def downgrade():
    # Remove the unique index
    op.drop_index("ix_players_substitute_identifier", "players")

    # Remove columns
    op.drop_column("active_rosters", "is_substitute")
    op.drop_constraint("fk_player_game_stats_playing_for_team", "player_game_stats", type_="foreignkey")
    op.drop_column("player_game_stats", "playing_for_team_id")
    op.drop_column("players", "is_substitute")
