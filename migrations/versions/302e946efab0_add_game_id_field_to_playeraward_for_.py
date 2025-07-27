"""Add game_id field to PlayerAward for per-game awards

Revision ID: 302e946efab0
Revises: 876bafcd6862
Create Date: 2025-07-27 15:00:51.080350

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "302e946efab0"
down_revision = "876bafcd6862"
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing unique constraint
    op.drop_constraint("unique_player_award", "player_awards", type_="unique")

    # Add game_id column for per-game awards (like dub_club)
    op.add_column("player_awards", sa.Column("game_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_player_awards_game_id", "player_awards", "games", ["game_id"], ["id"])

    # Create new unique constraint including game_id to allow multiple awards per player per week
    # but prevent duplicates for the same game
    op.create_unique_constraint(
        "unique_player_award", "player_awards", ["player_id", "award_type", "season", "week_date", "game_id"]
    )


def downgrade():
    # Drop the new unique constraint
    op.drop_constraint("unique_player_award", "player_awards", type_="unique")

    # Drop the foreign key and game_id column
    op.drop_constraint("fk_player_awards_game_id", "player_awards", type_="foreignkey")
    op.drop_column("player_awards", "game_id")

    # Restore the old unique constraint
    op.create_unique_constraint(
        "unique_player_award", "player_awards", ["player_id", "award_type", "season", "week_date"]
    )
