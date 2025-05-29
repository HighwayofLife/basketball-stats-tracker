"""
Service for importing roster and game stats from CSV files.
This module now delegates to the modular import system.
"""

from app.services.import_services import CSVParser, DataValidator, ImportOrchestrator, ImportProcessor


def import_roster_from_csv(roster_file: str, dry_run: bool = False) -> bool:
    """Import teams and players from a CSV file.

    Args:
        roster_file: Path to the roster CSV file
        dry_run: If True, validate but don't commit changes

    Returns:
        True on success, False on error
    """
    orchestrator = ImportOrchestrator()
    return orchestrator.import_roster_from_csv(roster_file, dry_run)


def import_game_stats_from_csv(game_stats_file: str, dry_run: bool = False) -> bool:
    """Import game statistics from a CSV file.

    Args:
        game_stats_file: Path to the game stats CSV file
        dry_run: If True, validate but don't commit changes

    Returns:
        True on success, False on error
    """
    orchestrator = ImportOrchestrator()
    return orchestrator.import_game_stats_from_csv(game_stats_file, dry_run)


# Expose internal functions for backward compatibility with tests
_check_file_exists = CSVParser.check_file_exists
_read_and_validate_roster_csv = CSVParser.read_roster_csv
_read_and_parse_game_stats_csv = CSVParser.read_game_stats_csv
_validate_game_stats_data = DataValidator.validate_game_stats_data
_extract_player_data_from_row = DataValidator._extract_player_data_from_row

# Create instance methods as module functions
_orchestrator = ImportOrchestrator()
_display_roster_import_summary = _orchestrator._display_roster_import_summary
_display_game_stats_import_summary = _orchestrator._display_game_stats_import_summary
_process_roster_import = _orchestrator._process_roster_import
_process_game_stats_import = _orchestrator._process_game_stats_import


# Processor functions need DB instance
def _process_teams(db, team_data):
    processor = ImportProcessor(db)
    return processor.process_teams(team_data)


def _process_players(db, player_data):
    processor = ImportProcessor(db)
    return processor.process_players(player_data)


def _record_player_stats(db, game, player_stats):
    processor = ImportProcessor(db)
    return processor._process_player_game_stats(game, player_stats)
