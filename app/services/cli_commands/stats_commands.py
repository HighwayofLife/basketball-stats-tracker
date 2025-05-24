"""Statistics-related CLI command handlers."""

import typer

from app.data_access.database_manager import db_manager
from app.services.season_stats_service import SeasonStatsService


class StatsCommands:
    """Handles statistics-related CLI commands."""

    @staticmethod
    def update_season_stats(season: str | None = None) -> None:
        """
        Update season statistics for all players and teams.
        This command recalculates all season statistics based on game data.

        Args:
            season: Season to update (e.g., '2024-2025'). If not specified, updates current season.
        """
        typer.echo(f"Updating season statistics{f' for {season}' if season else ' for current season'}...")

        with db_manager.get_db_session() as db_session:
            try:
                season_service = SeasonStatsService(db_session)
                season_service.update_all_season_stats(season)
                typer.echo("Season statistics updated successfully!")

            except Exception as e:  # pylint: disable=broad-except
                typer.echo(f"Error updating season statistics: {e}")
                typer.echo("Please check that the database has been initialized and contains game data.")
