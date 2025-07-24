"""refactor_player_awards_for_comprehensive_awards_support

Revision ID: 876bafcd6862
Revises: e0473a26cb0b
Create Date: 2025-07-23 21:22:04.039687

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "876bafcd6862"
down_revision = "e0473a26cb0b"
branch_labels = None
depends_on = None


def upgrade():
    # Drop the old unique constraint
    op.drop_constraint("unique_weekly_award", "player_awards", type_="unique")

    # Make week_date nullable for season awards
    op.alter_column("player_awards", "week_date", nullable=True)

    # Add new columns for comprehensive awards support
    op.add_column("player_awards", sa.Column("award_date", sa.Date(), nullable=True))
    op.add_column("player_awards", sa.Column("stat_value", sa.Float(), nullable=True))
    op.add_column("player_awards", sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default="0"))

    # Create new unique constraint allowing multiple award types per player per season
    op.create_unique_constraint(
        "unique_player_award", "player_awards", ["player_id", "award_type", "season", "week_date"]
    )


def downgrade():
    # Remove new columns
    op.drop_column("player_awards", "is_finalized")
    op.drop_column("player_awards", "stat_value")
    op.drop_column("player_awards", "award_date")

    # Drop new constraint
    op.drop_constraint("unique_player_award", "player_awards", type_="unique")

    # Make week_date non-nullable again
    op.alter_column("player_awards", "week_date", nullable=False)

    # Restore old unique constraint
    op.create_unique_constraint("unique_weekly_award", "player_awards", ["award_type", "week_date", "season"])
