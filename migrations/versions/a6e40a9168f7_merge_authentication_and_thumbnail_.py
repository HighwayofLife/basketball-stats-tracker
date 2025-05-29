"""Merge authentication and thumbnail migrations

Revision ID: a6e40a9168f7
Revises: add_thumbnail_image, add_user_auth_001
Create Date: 2025-05-28 19:53:20.485486

"""

# revision identifiers, used by Alembic.
revision = "a6e40a9168f7"
down_revision = ("add_thumbnail_image", "add_user_auth_001")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
