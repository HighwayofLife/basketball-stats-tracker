"""Add display_name field to Team model

Revision ID: 18b9a59ab7f2
Revises: ca9896e6a7f3
Create Date: 2025-05-26 14:03:36.835521

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "18b9a59ab7f2"
down_revision = "ca9896e6a7f3"
branch_labels = None
depends_on = None


def upgrade():
    # Add display_name column to teams table
    op.add_column("teams", sa.Column("display_name", sa.String(), nullable=True))

    # Update existing rows to set display_name = name
    op.execute("UPDATE teams SET display_name = name WHERE display_name IS NULL")


def downgrade():
    # Remove display_name column from teams table
    op.drop_column("teams", "display_name")
