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
    # Handle SQLite vs PostgreSQL differences
    from sqlalchemy import Date
    import sqlalchemy as sa
    
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        # SQLite doesn't support ALTER COLUMN TYPE, so we skip this migration
        # SQLite will just store dates as strings which works fine
        pass
    else:
        # PostgreSQL and other databases
        op.alter_column("games", "date", type_=Date(), postgresql_using="date::date")


def downgrade():
    # Handle SQLite vs PostgreSQL differences  
    from sqlalchemy import String
    
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        # SQLite doesn't support ALTER COLUMN TYPE, so we skip this migration
        pass
    else:
        # PostgreSQL and other databases
        op.alter_column("games", "date", type_=String(), postgresql_using="date::text")
