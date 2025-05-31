"""CLI commands for authentication management."""

import typer

from app.auth.models import UserRole
from app.auth.service import AuthService
from app.data_access.database_manager import db_manager


class AuthCommands:
    """Authentication-related CLI commands."""

    @staticmethod
    def create_admin_user(
        username: str,
        email: str,
        full_name: str | None = None,
    ) -> None:
        """Create an admin user.

        Args:
            username: Username for the admin
            email: Email address for the admin
            full_name: Optional full name
        """
        try:
            # Check for password in environment first, then prompt
            import os
            password = os.getenv("ADMIN_PASSWORD")
            
            if not password:
                # Prompt for password securely
                password = typer.prompt("Password", hide_input=True)
                password_confirm = typer.prompt("Confirm password", hide_input=True)
                
                if password != password_confirm:
                    typer.echo("❌ Passwords do not match.")
                    raise typer.Exit(1)
            
            with db_manager.get_db_session() as db:
                auth_service = AuthService(db)

                # Create admin user
                user = auth_service.create_user(
                    username=username, email=email, password=password, full_name=full_name, role=UserRole.ADMIN
                )

                typer.echo(f"✅ Admin user '{username}' created successfully!")
                typer.echo(f"   Email: {email}")
                typer.echo(f"   Role: {user.role.value}")

        except ValueError as e:
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"❌ Unexpected error: {e}")
            raise typer.Exit(1)

    @staticmethod
    def list_users() -> None:
        """List all users in the system."""
        try:
            with db_manager.get_db_session() as db:
                from app.auth.models import User

                users = db.query(User).all()

                if not users:
                    typer.echo("No users found.")
                    return

                typer.echo("\nUsers:")
                typer.echo("-" * 80)
                typer.echo(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<10} {'Active':<8}")
                typer.echo("-" * 80)

                for user in users:
                    active_status = "Yes" if user.is_active else "No"
                    typer.echo(
                        f"{user.id:<5} {user.username:<20} {user.email:<30} {user.role.value:<10} {active_status:<8}"
                    )

                typer.echo(f"\nTotal users: {len(users)}")

        except Exception as e:
            typer.echo(f"❌ Error listing users: {e}")
            raise typer.Exit(1)

    @staticmethod
    def deactivate_user(username: str) -> None:
        """Deactivate a user account.

        Args:
            username: Username of the user to deactivate
        """
        try:
            with db_manager.get_db_session() as db:
                auth_service = AuthService(db)

                # Find user
                user = auth_service.get_user_by_username(username)
                if not user:
                    typer.echo(f"❌ User '{username}' not found.")
                    raise typer.Exit(1)

                # Deactivate user
                if auth_service.deactivate_user(user.id):
                    typer.echo(f"✅ User '{username}' deactivated successfully.")
                else:
                    typer.echo(f"❌ Failed to deactivate user '{username}'.")
                    raise typer.Exit(1)

        except Exception as e:
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1)
        finally:
            if db:
                db.close()
