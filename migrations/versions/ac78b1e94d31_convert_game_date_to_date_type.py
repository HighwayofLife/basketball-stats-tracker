"""
Convert Game.date field from String to Date type.

Revision ID: ac78b1e94d31
Revises: 834c9663d23c
Create Date: 2025-05-21 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "ac78b1e94d31"
down_revision = "834c9663d23c"
branch_labels = None
depends_on = None


def upgrade():
    # Use Alembic's alter_column method instead of recreating the table
    # This is more database-agnostic
    from sqlalchemy import Date

    op.alter_column("games", "date", type_=Date(), postgresql_using="date::date")


def downgrade():
    # Use Alembic's alter_column method to revert the column type
    from sqlalchemy import String

    op.alter_column("games", "date", type_=String(), postgresql_using="date::text")
