"""Add player of the week awards count to Player model

Revision ID: 7e567a4a5d6e
Revises: 3d65696eeb09
Create Date: 2025-07-23 14:37:18.758002

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7e567a4a5d6e"
down_revision = "3d65696eeb09"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("players", schema=None) as batch_op:
        batch_op.add_column(sa.Column("player_of_the_week_awards", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("players", schema=None) as batch_op:
        batch_op.drop_column("player_of_the_week_awards")
