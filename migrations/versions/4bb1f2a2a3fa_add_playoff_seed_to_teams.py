"""add playoff_seed to teams

Revision ID: 4bb1f2a2a3fa
Revises: c2ca55dc5329
Create Date: 2025-07-28 14:17:04.818598

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4bb1f2a2a3fa"
down_revision = "c2ca55dc5329"
branch_labels = None
depends_on = None


def upgrade():
    # Add playoff_seed column to teams table
    op.add_column("teams", sa.Column("playoff_seed", sa.Integer(), nullable=True))


def downgrade():
    # Remove playoff_seed column from teams table
    op.drop_column("teams", "playoff_seed")
