"""Add unique constraint for games based on date and teams

Revision ID: ca9896e6a7f3
Revises: 4d2154170d95
Create Date: 2025-05-26 20:39:10.240203

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ca9896e6a7f3"
down_revision = "4d2154170d95"
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint to prevent duplicate games
    op.create_unique_constraint("uq_game_date_teams", "games", ["date", "playing_team_id", "opponent_team_id"])


def downgrade():
    # Remove the unique constraint
    op.drop_constraint("uq_game_date_teams", "games", type_="unique")
