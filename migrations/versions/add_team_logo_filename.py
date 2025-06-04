"""Add logo_filename field to Team model

Revision ID: add_team_logo_filename
Revises: add_scheduled_games_001
Create Date: 2025-06-03 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_team_logo_filename"
down_revision: str | None = "add_scheduled_games_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add logo_filename column to teams table
    op.add_column("teams", sa.Column("logo_filename", sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove logo_filename column from teams table
    op.drop_column("teams", "logo_filename")
