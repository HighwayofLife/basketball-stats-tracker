"""Add audit log and soft delete functionality

Revision ID: fd0f8271073e
Revises: 6c1432a982da
Create Date: 2025-05-23 02:00:12.429146

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'fd0f8271073e'
down_revision = '6c1432a982da'
branch_labels = None
depends_on = None


def upgrade():
    # Create audit_logs table
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=20), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('old_values', sa.JSON(), nullable=True),
    sa.Column('new_values', sa.JSON(), nullable=True),
    sa.Column('command_id', sa.String(length=36), nullable=True),
    sa.Column('is_undone', sa.Boolean(), nullable=False),
    sa.Column('undo_timestamp', sa.DateTime(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # Add soft delete columns to teams table
    op.add_column('teams', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('teams', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('teams', sa.Column('deleted_by', sa.Integer(), nullable=True))

    # Add soft delete columns to players table
    op.add_column('players', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('players', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('players', sa.Column('deleted_by', sa.Integer(), nullable=True))

    # Add soft delete columns to games table
    op.add_column('games', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('games', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('games', sa.Column('deleted_by', sa.Integer(), nullable=True))


def downgrade():
    # Remove soft delete columns from games table
    op.drop_column('games', 'deleted_by')
    op.drop_column('games', 'deleted_at')
    op.drop_column('games', 'is_deleted')

    # Remove soft delete columns from players table
    op.drop_column('players', 'deleted_by')
    op.drop_column('players', 'deleted_at')
    op.drop_column('players', 'is_deleted')

    # Remove soft delete columns from teams table
    op.drop_column('teams', 'deleted_by')
    op.drop_column('teams', 'deleted_at')
    op.drop_column('teams', 'is_deleted')

    # Drop audit_logs table
    op.drop_table('audit_logs')
