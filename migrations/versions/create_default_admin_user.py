"""Create default admin user for production

Revision ID: create_admin_001
Revises: add_user_auth_001
Create Date: 2025-05-30 00:00:00.000000

"""

import os
from datetime import datetime

import bcrypt
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "create_admin_001"
down_revision = "add_user_auth_001"
branch_labels = None
depends_on = None


def upgrade():
    """Create a default admin user for production access"""
    # Check if admin user already exists
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT COUNT(*) FROM users WHERE username = 'admin'"))
    admin_exists = result.scalar() > 0

    if not admin_exists:
        # Get password from environment variable (set by Terraform via Secret Manager)
        default_password = os.environ.get("DEFAULT_ADMIN_PASSWORD")

        if not default_password:
            raise RuntimeError("❌ DEFAULT_ADMIN_PASSWORD environment variable is not set. Migration aborted.")
        else:
            print("✅ Using secure password from DEFAULT_ADMIN_PASSWORD environment variable")

        # Hash the password
        hashed_password = bcrypt.hashpw(default_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Insert admin user
        connection.execute(
            sa.text("""
            INSERT INTO users (username, email, hashed_password, full_name, role, is_active, created_at, updated_at)
            VALUES ('admin', 'admin@league-stats.net', :hashed_password,
                    'System Administrator', 'admin', true, :now, :now)
        """),
            {"hashed_password": hashed_password, "now": datetime.utcnow()},
        )

        print("✅ Default admin user created: username='admin'")
        print("📝 Login at: https://league-stats.net/login")
        if not os.environ.get("DEFAULT_ADMIN_PASSWORD"):
            print("⚠️  IMPORTANT: Change the admin password after first login!")
    else:
        print("ℹ️  Admin user already exists, skipping creation")


def downgrade():
    """Remove the default admin user"""
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM users WHERE username = 'admin' AND email = 'admin@league-stats.net'"))
    print("🗑️  Default admin user removed")
