"""add oauth support and team association to users

Revision ID: 4277cc4a9e9c
Revises: 69cd99a5e5f6
Create Date: 2025-05-30 17:46:35.363516

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4277cc4a9e9c"
down_revision = "69cd99a5e5f6"
branch_labels = None
depends_on = None


def upgrade():
    # Add OAuth fields to users table
    op.add_column("users", sa.Column("provider", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("provider_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("team_id", sa.Integer(), nullable=True))

    # Create foreign key to teams table
    op.create_foreign_key("fk_users_team_id", "users", "teams", ["team_id"], ["id"])

    # Make hashed_password nullable for OAuth users
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)

    # Update existing users to have 'local' provider
    op.execute("UPDATE users SET provider = 'local' WHERE provider IS NULL")


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint("fk_users_team_id", "users", type_="foreignkey")

    # Remove columns
    op.drop_column("users", "team_id")
    op.drop_column("users", "provider_id")
    op.drop_column("users", "provider")

    # Make hashed_password non-nullable again
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
