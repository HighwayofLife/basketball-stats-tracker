"""Add thumbnail_image field to Player model

Revision ID: add_thumbnail_image
Revises: fd0f8271073e
Create Date: 2025-05-26 14:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_thumbnail_image"
down_revision: str | None = "18b9a59ab7f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add thumbnail_image column to players table
    op.add_column("players", sa.Column("thumbnail_image", sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove thumbnail_image column from players table
    op.drop_column("players", "thumbnail_image")
