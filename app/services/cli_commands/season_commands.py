"""Season-related CLI command handlers."""

from datetime import datetime

import typer
from tabulate import tabulate  # type: ignore

from app.data_access.db_session import get_db_session
from app.services.season_service import SeasonService


class SeasonCommands:
    """Handles season-related CLI commands."""

    @staticmethod
    def create_season(
        name: str,
        code: str,
        start: str,
        end: str,
        description: str | None = None,
        active: bool = False,
    ) -> None:
        """Create a new season.

        Args:
            name: Season name (e.g., 'Spring 2025')
            code: Unique season code (e.g., '2025-spring')
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            description: Season description
            active: Set as active season
        """
        with get_db_session() as session:
            try:
                # Parse dates
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
            except ValueError:
                typer.secho("Error: Invalid date format. Use YYYY-MM-DD", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)

            service = SeasonService(session)
            success, message, season = service.create_season(
                name=name,
                code=code,
                start_date=start_date,
                end_date=end_date,
                description=description,
                set_as_active=active,
            )

            if success:
                typer.secho(message, fg=typer.colors.GREEN)
                if season:
                    typer.echo(f"Season ID: {season.id}")
                    if active:
                        typer.echo("✓ Set as active season")
            else:
                typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)

    @staticmethod
    def list_seasons(active_only: bool = False) -> None:
        """List all seasons.

        Args:
            active_only: Show only active season
        """
        with get_db_session() as session:
            service = SeasonService(session)
            seasons = service.list_seasons(include_inactive=not active_only)

            if not seasons:
                typer.echo("No seasons found.")
                return

            # Prepare table data
            headers = ["ID", "Name", "Code", "Start", "End", "Games", "Status"]
            rows = []

            for season in seasons:
                status = "ACTIVE" if season["is_active"] else "Inactive"
                rows.append(
                    [
                        season["id"],
                        season["name"],
                        season["code"],
                        season["start_date"],
                        season["end_date"],
                        season["game_count"],
                        status,
                    ]
                )

            typer.echo("\nSeasons:")
            typer.echo(tabulate(rows, headers=headers, tablefmt="grid"))

    @staticmethod
    def activate_season(season_id: int) -> None:
        """Set a season as active.

        Args:
            season_id: Season ID to activate
        """
        with get_db_session() as session:
            service = SeasonService(session)
            success, message = service.set_active_season(season_id)

            if success:
                typer.secho(message, fg=typer.colors.GREEN)
            else:
                typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)

    @staticmethod
    def update_season(
        season_id: int,
        name: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
    ) -> None:
        """Update a season.

        Args:
            season_id: Season ID to update
            name: New season name
            start: New start date (YYYY-MM-DD)
            end: New end date (YYYY-MM-DD)
            description: New season description
        """
        if not any([name, start, end, description]):
            typer.secho("Error: At least one field must be provided to update", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        with get_db_session() as session:
            # Parse dates if provided
            start_date = None
            end_date = None
            if start:
                try:
                    start_date = datetime.strptime(start, "%Y-%m-%d").date()
                except ValueError:
                    typer.secho("Error: Invalid start date format. Use YYYY-MM-DD", fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1)
            if end:
                try:
                    end_date = datetime.strptime(end, "%Y-%m-%d").date()
                except ValueError:
                    typer.secho("Error: Invalid end date format. Use YYYY-MM-DD", fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1)

            service = SeasonService(session)
            success, message, season = service.update_season(
                season_id=season_id,
                name=name,
                start_date=start_date,
                end_date=end_date,
                description=description,
            )

            if success:
                typer.secho(message, fg=typer.colors.GREEN)
            else:
                typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)

    @staticmethod
    def delete_season(season_id: int, force: bool = False) -> None:
        """Delete a season (only if no games associated).

        Args:
            season_id: Season ID to delete
            force: Skip confirmation prompt
        """
        if not force:
            confirm = typer.confirm("Are you sure you want to delete this season?")
            if not confirm:
                typer.echo("Deletion cancelled.")
                raise typer.Exit()

        with get_db_session() as session:
            service = SeasonService(session)
            success, message = service.delete_season(season_id)

            if success:
                typer.secho(message, fg=typer.colors.GREEN)
            else:
                typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)

    @staticmethod
    def migrate_seasons(force: bool = False) -> None:
        """Migrate existing games to the new season system.

        Args:
            force: Skip confirmation prompt
        """
        if not force:
            confirm = typer.confirm("This will create seasons from existing data. Continue?")
            if not confirm:
                typer.echo("Migration cancelled.")
                raise typer.Exit()

        with get_db_session() as session:
            service = SeasonService(session)
            success, message = service.migrate_existing_games()

            if success:
                typer.secho(message, fg=typer.colors.GREEN)
            else:
                typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
