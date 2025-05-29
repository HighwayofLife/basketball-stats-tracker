#!/usr/bin/env python3
"""
CLI interface for the Basketball Stats Tracker application.
Provides commands for database initialization, maintenance, and reporting.
"""

import typer

from app.services.cli_commands import (
    AuthCommands,
    DatabaseCommands,
    ImportCommands,
    ListingCommands,
    ReportCommands,
    ServerCommands,
    StatsCommands,
)

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
    DatabaseCommands.initialize_database(force=force, make_migration=make_migration)


@cli.command("health-check")
def check_database_health():
    """
    Check if the database is properly set up and accessible.
    """
    return DatabaseCommands.check_database_health()


@cli.command("seed-db")
def seed_database():
    """
    Seed the database with initial data for development and testing.

    This will add teams, players, and sample games to the database.
    """
    DatabaseCommands.seed_database()


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
    return ImportCommands.import_roster(file, dry_run)


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
    return ImportCommands.import_game_stats(file, dry_run)


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
    show_options: bool = typer.Option(False, "--show-options", help="Show available reports and parameters for a game"),
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
    ReportCommands.generate_report(
        game_id=game_id,
        report_type=report_type,
        player_id=player_id,
        team_id=team_id,
        show_options=show_options,
        output_format=output_format,
        output_file=output_file,
    )


@cli.command("mcp-server")
def start_mcp_server():
    """
    Start the Model Context Protocol (MCP) server for SQL queries and natural language processing.

    This server provides API access to the basketball stats database via HTTP endpoints.
    """
    ServerCommands.start_mcp_server()


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
    ServerCommands.start_web_server(host=host, port=port, reload=reload)


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
    ReportCommands.generate_season_report(
        season=season,
        report_type=report_type,
        stat_category=stat_category,
        player_id=player_id,
        team_id=team_id,
        limit=limit,
        min_games=min_games,
        output_format=output_format,
        output_file=output_file,
    )


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
    StatsCommands.update_season_stats(season)


@cli.command("list-games")
def list_games(
    team: str = typer.Option(None, "--team", "-t", help="Filter by team name (home or away)"),
    from_date: str = typer.Option(None, "--from", "-f", help="Filter by start date (YYYY-MM-DD)"),
    to_date: str = typer.Option(None, "--to", help="Filter by end date (YYYY-MM-DD)"),
    season: str = typer.Option(None, "--season", "-s", help="Filter by season (e.g., '2024-2025')"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show more details"),
    output_format: str = typer.Option("console", "--format", help="Output format: console or csv"),
    output_file: str = typer.Option(None, "--output", "-o", help="File path for CSV output"),
):
    """
    List all games with optional filtering.

    Examples:
        basketball-stats list-games
        basketball-stats list-games --team "Lakers"
        basketball-stats list-games --from "2024-12-01" --to "2024-12-31"
        basketball-stats list-games --season "2024-2025"
        basketball-stats list-games --detailed
    """
    ListingCommands.list_games(
        team=team,
        from_date=from_date,
        to_date=to_date,
        season=season,
        detailed=detailed,
        output_format=output_format,
        output_file=output_file,
    )


@cli.command("list-players")
def list_players(
    team: str = typer.Option(None, "--team", "-t", help="Filter by team name"),
    name: str = typer.Option(None, "--name", "-n", help="Search by player name (partial match)"),
    position: str = typer.Option(None, "--position", "-p", help="Filter by position"),
    output_format: str = typer.Option("console", "--format", help="Output format: console or csv"),
    output_file: str = typer.Option(None, "--output", "-o", help="File path for CSV output"),
):
    """
    List all players with optional filtering.

    Examples:
        basketball-stats list-players
        basketball-stats list-players --team "Lakers"
        basketball-stats list-players --name "LeBron"
        basketball-stats list-players --position "PG"
    """
    ListingCommands.list_players(
        team=team,
        name=name,
        position=position,
        output_format=output_format,
        output_file=output_file,
    )


@cli.command("list-teams")
def list_teams(
    with_players: bool = typer.Option(False, "--with-players", "-p", help="Show team rosters"),
    output_format: str = typer.Option("console", "--format", help="Output format: console or csv"),
    output_file: str = typer.Option(None, "--output", "-o", help="File path for CSV output"),
):
    """
    List all teams.

    Examples:
        basketball-stats list-teams
        basketball-stats list-teams --with-players
    """
    ListingCommands.list_teams(
        with_players=with_players,
        output_format=output_format,
        output_file=output_file,
    )


@cli.command("create-admin")
def create_admin_user(
    username: str = typer.Argument(..., help="Username for the admin user"),
    email: str = typer.Argument(..., help="Email address for the admin user"),
    full_name: str = typer.Option(None, "--name", "-n", help="Full name of the admin user"),
):
    """
    Create an admin user for the system.

    You will be prompted to enter a password.

    Example:
        basketball-stats create-admin admin admin@example.com --name "Admin User"
    """
    AuthCommands.create_admin_user(username=username, email=email, full_name=full_name)


@cli.command("list-users")
def list_users():
    """List all users in the system."""
    AuthCommands.list_users()


@cli.command("deactivate-user")
def deactivate_user(
    username: str = typer.Argument(..., help="Username of the user to deactivate"),
):
    """
    Deactivate a user account.

    The user will no longer be able to log in.

    Example:
        basketball-stats deactivate-user john_doe
    """
    AuthCommands.deactivate_user(username=username)


if __name__ == "__main__":
    cli()
