"""Import-related CLI command handlers."""

from app.services.csv_import_service import import_game_stats_from_csv, import_roster_from_csv


class ImportCommands:
    """Handles import-related CLI commands."""

    @staticmethod
    def import_roster(file: str, dry_run: bool = False) -> None:
        """
        Import teams and players from a CSV file.

        Args:
            file: Path to the CSV file containing the roster
            dry_run: Preview what would be imported without making changes
        """
        return import_roster_from_csv(file, dry_run)

    @staticmethod
    def import_game_stats(file: str, dry_run: bool = False) -> None:
        """
        Import game statistics from a CSV file.

        Args:
            file: Path to the CSV file containing the game statistics
            dry_run: Preview what would be imported without making changes
        """
        return import_game_stats_from_csv(file, dry_run)
