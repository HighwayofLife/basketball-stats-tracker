#!/usr/bin/env python3
"""
CLI interface for the Basketball Stats Tracker application.
Provides commands for database initialization, maintenance, and reporting.
"""

import csv
import logging

import typer
import uvicorn
from tabulate import tabulate  # type: ignore

from app.config import settings
from app.data_access.database_manager import db_manager  # Corrected import
from app.reports.report_generator import ReportGenerator
from app.utils import stats_calculator

cli = typer.Typer(help="Basketball Stats Tracker CLI")


@cli.command("init-db")
def initialize_database(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force recreation of tables even if they already exist (WARNING: This will delete all data)",
    ),
    make_migration: bool = typer.Option(
        False,
        "--migration",
        "-m",
        help="Create a new migration based on model changes",
    ),
):
    """
    Initialize or upgrade the database schema using Alembic migrations.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.database_admin_service import DatabaseAdminService

    db_url = settings.DATABASE_URL
    admin_service = DatabaseAdminService(db_url)
    admin_service.initialize_schema(force=force, make_migration=make_migration)


@cli.command("health-check")
def check_database_health():
    """
    Check if the database is properly set up and accessible.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.database_admin_service import DatabaseAdminService

    db_url = settings.DATABASE_URL
    admin_service = DatabaseAdminService(db_url)
    if admin_service.check_connection():
        typer.echo("Database connection successful!")
        return True

    typer.echo("Database connection test failed!")
    return False


@cli.command("seed-db")
def seed_database():
    """
    Seed the database with initial data for development and testing.

    This will add teams, players, and sample games to the database.
    """
    typer.echo("Seeding database with development data...")

    # Import the seed script
    # pylint: disable=wrong-import-position
    # pylint: disable=import-outside-toplevel
    from seed import seed_all

    # Run the seed function
    seed_all()

    typer.echo("Database seeding completed.")


@cli.command("import-roster")
def import_roster(
    file: str = typer.Option(
        ...,  # Makes this parameter required
        "--file",
        "-f",
        help="Path to the CSV file containing the roster (team names, player names, jersey numbers)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview what would be imported without making any changes to the database",
    ),
):
    """
    Import teams and players from a CSV file.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.csv_import_service import import_roster_from_csv

    return import_roster_from_csv(file, dry_run)


@cli.command("import-game")
def import_game_stats(
    file: str = typer.Option(
        ...,  # Makes this parameter required
        "--file",
        "-f",
        help="Path to the CSV file containing the game statistics",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview what would be imported without making any changes to the database",
    ),
):
    """
    Import game statistics from a CSV file.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.csv_import_service import import_game_stats_from_csv

    return import_game_stats_from_csv(file, dry_run)


@cli.command("report")
def generate_report(
    game_id: int = typer.Option(..., "--id", "-i", help="ID of the game to generate the report for"),
    report_type: str = typer.Option(
        "box-score",
        "--type",
        "-t",
        help="Type of report: box-score, player-performance, team-efficiency, scoring-analysis, or game-flow",
    ),
    player_id: int = typer.Option(None, "--player", "-p", help="Player ID (required for player-performance report)"),
    team_id: int = typer.Option(
        None, "--team", "--team-id", help="Team ID (required for team-efficiency and scoring-analysis reports)"
    ),
    output_format: str = typer.Option("console", "--format", "-f", help="Output format: console or csv"),
    output_file: str = typer.Option(
        None,
        "--output",
        "-o",
        help="File path for output when using csv format",
    ),
):
    """
    Generate a statistical report for a specific game.

    Several report types are available:
    - box-score: Traditional box score with player and team stats
    - player-performance: Detailed analysis of a single player's performance
    - team-efficiency: Analysis of a team's offensive efficiency
    - scoring-analysis: Breakdown of how a team generated points
    - game-flow: Quarter-by-quarter analysis of game momentum
    """
    with db_manager.get_db_session() as db_session:  # Use the imported db_manager
        try:
            report_generator = ReportGenerator(db_session, stats_calculator)

            # Generate the appropriate report based on type
            if report_type == "box-score":
                player_stats, game_summary = report_generator.get_game_box_score_data(game_id)
                report_data = {"player_stats": player_stats, "game_summary": game_summary}

            elif report_type == "player-performance":
                if not player_id:
                    typer.echo("Error: Player ID is required for player-performance report.")
                    return
                report_data = report_generator.generate_player_performance_report(player_id, game_id)

            elif report_type == "team-efficiency":
                if not team_id:
                    typer.echo("Error: Team ID is required for team-efficiency report.")
                    return
                report_data = report_generator.generate_team_efficiency_report(team_id, game_id)

            elif report_type == "scoring-analysis":
                if not team_id:
                    typer.echo("Error: Team ID is required for scoring-analysis report.")
                    return
                report_data = report_generator.generate_scoring_analysis_report(team_id, game_id)

            elif report_type == "game-flow":
                report_data = report_generator.generate_game_flow_report(game_id)

            else:
                typer.echo(f"Error: Unknown report type '{report_type}'")
                return

            if not report_data:
                typer.echo(f"No data found for {report_type} with game ID: {game_id}")
                return

            # Output the report in the requested format
            if output_format == "console":
                typer.echo(f"{report_type.title()} Report for Game ID: {game_id}")

                if report_type == "box-score":
                    # Box score has special formatting with player stats and game summary
                    typer.echo("\nPlayer Stats:")
                    typer.echo(tabulate(report_data["player_stats"], headers="keys", tablefmt="grid"))

                    if report_data["game_summary"]:
                        typer.echo("\nGame Summary:")
                        if isinstance(report_data["game_summary"], dict):
                            for key, value in report_data["game_summary"].items():
                                typer.echo(f"{key.replace('_', ' ').title()}: {value}")
                        else:
                            # Handle non-dictionary game summary
                            typer.echo(str(report_data["game_summary"]))
                else:
                    # For other report types, format based on data structure
                    _display_report_console(report_data)

            elif output_format == "csv":
                csv_file_name = output_file if output_file else f"game_{game_id}_{report_type}.csv"
                with open(csv_file_name, "w", newline="", encoding="utf-8") as csvfile:
                    if (
                        report_type == "box-score"
                        and report_data["player_stats"]
                        and isinstance(report_data["player_stats"], list)
                        and len(report_data["player_stats"]) > 0
                    ):
                        writer = csv.DictWriter(csvfile, fieldnames=report_data["player_stats"][0].keys())
                        writer.writeheader()
                        writer.writerows(report_data["player_stats"])
                    else:
                        _write_report_to_csv(report_data, csvfile)

                typer.echo(f"Report generated: {csv_file_name}")
            else:
                typer.echo(f"Unsupported format: {output_format}. Choose 'console' or 'csv'.")

        except (ValueError, KeyError, TypeError) as e:
            typer.echo(f"Data error occurred: {e}")
        except FileNotFoundError as e:
            typer.echo(f"File error: {e}")
        except ImportError as e:
            typer.echo(f"Module import error: {e}")
        except Exception as e:  # pylint: disable=broad-except
            typer.echo(f"Unexpected error: {e}")
            typer.echo("Please report this issue with the steps to reproduce it")


@cli.command("mcp-server")
def start_mcp_server():
    """
    Start the Model Context Protocol (MCP) server for SQL queries and natural language processing.

    This server provides API access to the basketball stats database via HTTP endpoints.
    """
    typer.echo("Starting MCP Server...")
    # pylint: disable=import-outside-toplevel
    from app.mcp_server import start

    start()


@cli.command("web-server")
def web_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
):
    """
    Start the web UI server with FastAPI.

    Args:
        host: The host IP to bind the server to
        port: The port to run the server on
        reload: Whether to reload the server on code changes (development only)
    """
    logging.info("Starting web UI server on %s:%d", host, port)

    # Start the server
    uvicorn.run(
        "app.web_ui.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def _display_report_console(report_data):
    """
    Display a report in the console.

    Args:
        report_data: Dictionary containing the report data
    """
    # Recursively print nested dictionaries and lists
    _print_nested_data(report_data)


def _print_nested_data(data, indent=0):
    """
    Recursively print nested dictionaries and lists with proper indentation.

    Args:
        data: Data to print (dictionary, list, or scalar value)
        indent: Current indentation level
    """
    indent_str = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict | list):
                typer.echo(f"{indent_str}{key.replace('_', ' ').title()}:")
                _print_nested_data(value, indent + 1)
            else:
                # Format special values
                if key.endswith("_pct") and value is not None:
                    value = f"{value:.3f}"
                typer.echo(f"{indent_str}{key.replace('_', ' ').title()}: {value}")
    elif isinstance(data, list):
        # Special handling for lists of dictionaries - use tabulate if they have the same keys
        if data and all(isinstance(item, dict) for item in data) and len({tuple(item.keys()) for item in data}) == 1:
            typer.echo(tabulate(data, headers="keys", tablefmt="grid"))
            return

        # Otherwise, just print each item with indentation
        for i, item in enumerate(data):
            if isinstance(item, dict | list):
                typer.echo(f"{indent_str}Item {i + 1}:")
                _print_nested_data(item, indent + 1)
            else:
                typer.echo(f"{indent_str}- {item}")
    else:
        typer.echo(f"{indent_str}{data}")


def _write_report_to_csv(report_data, csvfile):
    """
    Write a report to a CSV file.

    Args:
        report_data: Dictionary containing the report data
        csvfile: File object to write to
    """
    # Handle different report structures
    writer = csv.writer(csvfile)

    if isinstance(report_data, dict):
        # Write a header row with "Field" and "Value"
        writer.writerow(["Field", "Value"])
        _write_dict_to_csv(report_data, writer)
    elif isinstance(report_data, list):
        # If it's a list of dictionaries with the same keys, write as a table
        if (
            report_data
            and all(isinstance(item, dict) for item in report_data)
            and len({tuple(item.keys()) for item in report_data}) == 1
        ):
            dict_writer = csv.DictWriter(csvfile, fieldnames=report_data[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(report_data)
            return

        # Otherwise, just write each item
        for item in report_data:
            _write_value_to_csv(item, writer)


def _write_dict_to_csv(data, writer, prefix=""):
    """
    Recursively write a dictionary to a CSV writer.

    Args:
        data: Dictionary to write
        writer: CSV writer object
        prefix: Prefix for nested keys
    """
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        _write_value_to_csv(value, writer, full_key)


def _write_value_to_csv(value, writer, key=None):
    """
    Write a value to a CSV writer.

    Args:
        value: Value to write
        writer: CSV writer object
        key: Key for the value (if any)
    """
    key_str = "" if key is None else key

    if isinstance(value, dict):
        _write_dict_to_csv(value, writer, key_str)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            item_key = f"{key_str}[{i}]" if key_str else f"Item {i + 1}"
            _write_value_to_csv(item, writer, item_key)
    else:
        if key_str:
            writer.writerow([key_str.replace("_", " ").title(), value])


@cli.command("season-report")
def generate_season_report(
    season: str = typer.Option(
        None,
        "--season",
        "-s",
        help="Season to generate report for (e.g., '2024-2025'). If not specified, uses current season.",
    ),
    report_type: str = typer.Option(
        "standings",
        "--type",
        "-t",
        help="Type of report: standings, player-leaders, team-stats, or player-season",
    ),
    stat_category: str = typer.Option(
        "ppg",
        "--stat",
        help="Stat category for player-leaders: ppg, fpg, ft_pct, fg_pct, fg3_pct, efg_pct",
    ),
    player_id: int = typer.Option(None, "--player", "-p", help="Player ID (required for player-season report)"),
    team_id: int = typer.Option(None, "--team", help="Team ID (optional for filtering)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of players to show in leaderboards"),
    min_games: int = typer.Option(1, "--min-games", help="Minimum games played for leaderboards"),
    output_format: str = typer.Option("console", "--format", "-f", help="Output format: console or csv"),
    output_file: str = typer.Option(None, "--output", "-o", help="File path for output when using csv format"),
):
    """
    Generate season-long statistical reports.

    Several report types are available:
    - standings: Team standings with win/loss records
    - player-leaders: Top players in various statistical categories
    - team-stats: Detailed team statistics for the season
    - player-season: Individual player's season statistics
    """
    # pylint: disable=import-outside-toplevel
    from app.services.season_stats_service import SeasonStatsService
    from app.utils.stats_calculator import calculate_efg, calculate_percentage

    with db_manager.get_db_session() as db_session:
        try:
            season_service = SeasonStatsService(db_session)

            # Generate the appropriate report based on type
            if report_type == "standings":
                report_data = season_service.get_team_standings(season)
                report_title = f"Team Standings{f' - {season}' if season else ''}"

            elif report_type == "player-leaders":
                report_data = season_service.get_player_rankings(
                    stat_category=stat_category, season=season, limit=limit, min_games=min_games
                )
                stat_name = {
                    "ppg": "Points Per Game",
                    "fpg": "Fouls Per Game",
                    "ft_pct": "Free Throw Percentage",
                    "fg_pct": "Field Goal Percentage",
                    "fg3_pct": "3-Point Percentage",
                    "efg_pct": "Effective Field Goal Percentage",
                }.get(stat_category, stat_category)
                report_title = f"Player Leaders - {stat_name}{f' ({season})' if season else ''}"

            elif report_type == "team-stats":
                if team_id:
                    # pylint: disable=import-outside-toplevel
                    from app.data_access.crud import get_team_season_stats

                    team_stats = get_team_season_stats(db_session, team_id, season)
                    if team_stats:
                        report_data = [
                            {
                                "team_id": team_stats.team_id,
                                "team_name": team_stats.team.name,
                                "season": team_stats.season,
                                "games_played": team_stats.games_played,
                                "wins": team_stats.wins,
                                "losses": team_stats.losses,
                                "win_pct": (
                                    team_stats.wins / team_stats.games_played if team_stats.games_played > 0 else 0
                                ),
                                "ppg": (
                                    team_stats.total_points_for / team_stats.games_played
                                    if team_stats.games_played > 0
                                    else 0
                                ),
                                "opp_ppg": (
                                    team_stats.total_points_against / team_stats.games_played
                                    if team_stats.games_played > 0
                                    else 0
                                ),
                                "ft_pct": calculate_percentage(team_stats.total_ftm, team_stats.total_fta),
                                "fg_pct": calculate_percentage(
                                    team_stats.total_2pm + team_stats.total_3pm,
                                    team_stats.total_2pa + team_stats.total_3pa,
                                ),
                                "fg3_pct": calculate_percentage(team_stats.total_3pm, team_stats.total_3pa),
                            }
                        ]
                    else:
                        report_data = []
                else:
                    # Get all team stats for the season
                    # pylint: disable=import-outside-toplevel
                    from app.data_access.crud.crud_team_season_stats import get_season_teams

                    all_team_stats: list = get_season_teams(db_session, season)
                    report_data = []
                    for ts in all_team_stats:
                        report_data.append(
                            {
                                "team_id": ts.team_id,
                                "team_name": ts.team.name,
                                "games_played": ts.games_played,
                                "wins": ts.wins,
                                "losses": ts.losses,
                                "win_pct": ts.wins / ts.games_played if ts.games_played > 0 else 0,
                                "ppg": ts.total_points_for / ts.games_played if ts.games_played > 0 else 0,
                                "opp_ppg": ts.total_points_against / ts.games_played if ts.games_played > 0 else 0,
                            }
                        )
                report_title = f"Team Statistics{f' - {season}' if season else ''}"

            elif report_type == "player-season":
                if not player_id:
                    typer.echo("Error: Player ID is required for player-season report.")
                    return

                # pylint: disable=import-outside-toplevel
                from app.data_access.crud import get_player_by_id, get_player_season_stats

                player = get_player_by_id(db_session, player_id)
                if not player:
                    typer.echo(f"Error: Player with ID {player_id} not found.")
                    return

                player_stats = get_player_season_stats(db_session, player_id, season)
                if player_stats:
                    total_points = player_stats.total_ftm + (player_stats.total_2pm * 2) + (player_stats.total_3pm * 3)
                    report_data = [
                        {
                            "player_name": player.name,
                            "team_name": player.team.name,
                            "season": player_stats.season,
                            "games_played": player_stats.games_played,
                            "total_points": total_points,
                            "ppg": total_points / player_stats.games_played if player_stats.games_played > 0 else 0,
                            "total_fouls": player_stats.total_fouls,
                            "fpg": (
                                player_stats.total_fouls / player_stats.games_played
                                if player_stats.games_played > 0
                                else 0
                            ),
                            "ft_pct": calculate_percentage(player_stats.total_ftm, player_stats.total_fta),
                            "fg_pct": calculate_percentage(
                                player_stats.total_2pm + player_stats.total_3pm,
                                player_stats.total_2pa + player_stats.total_3pa,
                            ),
                            "fg3_pct": calculate_percentage(player_stats.total_3pm, player_stats.total_3pa),
                            "efg_pct": calculate_efg(
                                player_stats.total_2pm + player_stats.total_3pm,
                                player_stats.total_3pm,
                                player_stats.total_2pa + player_stats.total_3pa,
                            ),
                        }
                    ]
                else:
                    report_data = []
                report_title = f"{player.name} - Season Statistics{f' ({season})' if season else ''}"

            else:
                typer.echo(f"Error: Unknown report type '{report_type}'")
                return

            if not report_data:
                typer.echo(f"No data found for {report_type} report{f' for season {season}' if season else ''}")
                return

            # Output the report in the requested format
            if output_format == "console":
                typer.echo(f"\n{report_title}")
                typer.echo("=" * len(report_title))
                if report_data:
                    typer.echo(tabulate(report_data, headers="keys", tablefmt="grid", floatfmt=".3f"))

            elif output_format == "csv":
                csv_file_name = output_file if output_file else f"season_{report_type}_{season or 'current'}.csv"
                with open(csv_file_name, "w", newline="", encoding="utf-8") as csvfile:
                    if report_data and isinstance(report_data, list) and len(report_data) > 0:
                        writer = csv.DictWriter(csvfile, fieldnames=report_data[0].keys())
                        writer.writeheader()
                        writer.writerows(report_data)
                typer.echo(f"Report generated: {csv_file_name}")
            else:
                typer.echo(f"Unsupported format: {output_format}. Choose 'console' or 'csv'.")

        except Exception as e:  # pylint: disable=broad-except
            typer.echo(f"Error generating season report: {e}")
            typer.echo("Please check that the database has been initialized and contains data.")


@cli.command("update-season-stats")
def update_season_stats(
    season: str = typer.Option(
        None,
        "--season",
        "-s",
        help="Season to update (e.g., '2024-2025'). If not specified, updates current season.",
    ),
):
    """
    Update season statistics for all players and teams.

    This command recalculates all season statistics based on game data.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.season_stats_service import SeasonStatsService

    typer.echo(f"Updating season statistics{f' for {season}' if season else ' for current season'}...")

    with db_manager.get_db_session() as db_session:
        try:
            season_service = SeasonStatsService(db_session)

            season_service.update_all_season_stats(season)

            typer.echo("Season statistics updated successfully!")

        except Exception as e:  # pylint: disable=broad-except
            typer.echo(f"Error updating season statistics: {e}")
            typer.echo("Please check that the database has been initialized and contains game data.")


if __name__ == "__main__":
    cli()
