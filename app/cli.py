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
    SeasonCommands,
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


# Season Management Commands
@cli.command("season-create")
def create_season(
    name: str = typer.Option(..., "--name", "-n", help="Season name (e.g., 'Spring 2025')"),
    code: str = typer.Option(..., "--code", "-c", help="Unique season code (e.g., '2025-spring')"),
    start: str = typer.Option(..., "--start", "-s", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", "-e", help="End date (YYYY-MM-DD)"),
    description: str = typer.Option(None, "--description", "-d", help="Season description"),
    active: bool = typer.Option(False, "--active", help="Set as active season"),
):
    """
    Create a new season.

    Example:
        basketball-stats season-create --name "Spring 2025" --code "2025-spring" \\
            --start 2025-03-01 --end 2025-06-30 --active
    """
    SeasonCommands.create_season(
        name=name,
        code=code,
        start=start,
        end=end,
        description=description,
        active=active,
    )


@cli.command("season-list")
def list_seasons(
    active_only: bool = typer.Option(False, "--active-only", help="Show only active season"),
):
    """
    List all seasons.

    Example:
        basketball-stats season-list
        basketball-stats season-list --active-only
    """
    SeasonCommands.list_seasons(active_only=active_only)


@cli.command("season-activate")
def activate_season(
    season_id: int = typer.Argument(..., help="Season ID to activate"),
):
    """
    Set a season as active.

    Example:
        basketball-stats season-activate 1
    """
    SeasonCommands.activate_season(season_id=season_id)


@cli.command("season-update")
def update_season(
    season_id: int = typer.Argument(..., help="Season ID to update"),
    name: str = typer.Option(None, "--name", "-n", help="New season name"),
    start: str = typer.Option(None, "--start", "-s", help="New start date (YYYY-MM-DD)"),
    end: str = typer.Option(None, "--end", "-e", help="New end date (YYYY-MM-DD)"),
    description: str = typer.Option(None, "--description", "-d", help="New season description"),
):
    """
    Update a season.

    Example:
        basketball-stats season-update 1 --name "Spring League 2025" --end 2025-07-15
    """
    SeasonCommands.update_season(
        season_id=season_id,
        name=name,
        start=start,
        end=end,
        description=description,
    )


@cli.command("season-delete")
def delete_season(
    season_id: int = typer.Argument(..., help="Season ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """
    Delete a season (only if no games associated).

    Example:
        basketball-stats season-delete 1
        basketball-stats season-delete 1 --force
    """
    SeasonCommands.delete_season(season_id=season_id, force=force)


@cli.command("season-migrate")
def migrate_seasons(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """
    Migrate existing games to the new season system.

    This will create seasons from existing data and assign games to appropriate seasons.

    Example:
        basketball-stats season-migrate
        basketball-stats season-migrate --force
    """
    SeasonCommands.migrate_seasons(force=force)


@cli.command("calculate-potw")
def calculate_potw(
    season: str = typer.Option(
        None,
        "--season",
        help="Calculate for specific season (e.g., '2024'). If not provided, calculates for all seasons.",
    ),
    recalculate: bool = typer.Option(
        False, "--recalculate", help="Reset existing awards and recalculate from scratch."
    ),
):
    """
    Calculate Player of the Week awards for games.

    Examples:
        basketball-stats calculate-potw                    # Calculate for all seasons
        basketball-stats calculate-potw --season 2024      # Calculate for 2024 season
        basketball-stats calculate-potw --recalculate      # Reset and recalculate all awards
    """
    from app.dependencies import get_db
    from app.services.awards_service import calculate_player_of_the_week, get_current_season

    db_session = next(get_db())

    try:
        # Validate season format if provided
        if season and not season.isdigit():
            typer.echo(f"Error: Season must be a 4-digit year (e.g., '2024'), got: {season}", err=True)
            raise typer.Exit(1)

        if recalculate:
            typer.echo("⚠️  Recalculating all Player of the Week awards (this will reset existing awards)")

        current_season = get_current_season()
        season_display = season or "all seasons"
        typer.echo(f"🏀 Calculating Player of the Week awards for {season_display}...")
        typer.echo(f"📅 Current season: {current_season}")

        results = calculate_player_of_the_week(db_session, season=season, recalculate=recalculate)

        if results:
            typer.echo("✅ Awards calculated successfully!")
            typer.echo("\n📊 Awards given by season:")
            for season_key, count in sorted(results.items()):
                typer.echo(f"   {season_key}: {count} awards")

            total_awards = sum(results.values())
            typer.echo(f"\n🏆 Total awards given: {total_awards}")
        else:
            typer.echo("ℹ️  No awards were given (no games found or no player stats)")

    except Exception as e:
        typer.echo(f"❌ Error calculating awards: {str(e)}", err=True)
        raise typer.Exit(1) from e


@cli.command("calculate-season-awards")
def calculate_season_awards(
    season: str = typer.Option(
        None,
        "--season",
        help="Calculate for specific season (e.g., '2024'). If not provided, calculates current season.",
    ),
    recalculate: bool = typer.Option(
        False, "--recalculate", help="Reset existing awards and recalculate from scratch."
    ),
):
    """
    Calculate season awards (Top Scorer, Sharpshooter, etc.).

    Examples:
        basketball-stats calculate-season-awards                        # Calculate current season
        basketball-stats calculate-season-awards --season 2024         # Calculate 2024 season
        basketball-stats calculate-season-awards --recalculate         # Reset and recalculate
    """
    from app.config_data.awards import SEASON_AWARDS
    from app.dependencies import get_db
    from app.services.awards_service import calculate_all_season_awards, get_current_season

    db_session = next(get_db())

    try:
        # Validate season format if provided
        if season and not season.isdigit():
            typer.echo(f"Error: Season must be a 4-digit year (e.g., '2024'), got: {season}", err=True)
            raise typer.Exit(1)

        if recalculate:
            typer.echo("⚠️  Recalculating season awards (this will reset existing awards)")

        current_season = get_current_season()
        target_season = season or current_season
        typer.echo(f"🏆 Calculating season awards for {target_season}...")

        results = calculate_all_season_awards(db_session, season=target_season, recalculate=recalculate)

        if results:
            typer.echo("✅ Season awards calculated successfully!")
            typer.echo(f"\n📊 Awards given for season {target_season}:")

            for award_key, season_results in results.items():
                display_name = SEASON_AWARDS.get(award_key, {}).get("name", award_key)
                typer.echo(f"   {display_name}: {season_results.get(target_season, 0)} awards")

            total_awards = sum(sum(season_data.values()) for season_data in results.values())
            typer.echo(f"\n🏆 Total season awards given: {total_awards}")
        else:
            typer.echo("ℹ️  No awards were given (no games found or no player stats)")

    except Exception as e:
        typer.echo(f"❌ Error calculating season awards: {str(e)}", err=True)
        raise typer.Exit(1) from e


@cli.command("calculate-weekly-awards")
def calculate_weekly_awards(
    season: str = typer.Option(
        None,
        "--season",
        help="Calculate for specific season (e.g., '2024'). If not provided, calculates for all seasons.",
    ),
    recalculate: bool = typer.Option(
        False, "--recalculate", help="Reset existing awards and recalculate from scratch."
    ),
    award_type: str = typer.Option(
        None,
        "--type",
        help="Calculate specific award type only (e.g., 'quarterly_firepower')",
    ),
):
    """
    Calculate all weekly awards (POTW, Quarterly Firepower, Hot Hand, etc.).

    Examples:
        basketball-stats calculate-weekly-awards                           # Calculate all seasons
        basketball-stats calculate-weekly-awards --season 2024            # Calculate 2024 season
        basketball-stats calculate-weekly-awards --type hot_hand_weekly   # Calculate only Hot Hand
        basketball-stats calculate-weekly-awards --recalculate            # Reset and recalculate
    """
    from app.dependencies import get_db
    from app.services.awards_service import calculate_all_weekly_awards, get_current_season

    db_session = next(get_db())

    try:
        # Validate season format if provided
        if season and not season.isdigit():
            typer.echo(f"Error: Season must be a 4-digit year (e.g., '2024'), got: {season}", err=True)
            raise typer.Exit(1)

        if recalculate:
            typer.echo("⚠️  Recalculating weekly awards (this will reset existing awards)")

        current_season = get_current_season()
        season_display = season or "all seasons"
        typer.echo(f"📅 Calculating weekly awards for {season_display}...")
        typer.echo(f"📅 Current season: {current_season}")

        if award_type:
            typer.echo(f"🎯 Calculating only: {award_type}")

        results = calculate_all_weekly_awards(db_session, season=season, recalculate=recalculate)

        if results:
            typer.echo("✅ Weekly awards calculated successfully!")

            award_names = {
                "player_of_the_week": "🏀 Player of the Week",
                "quarterly_firepower": "🔥 Quarterly Firepower",
                "weekly_ft_king": "👑 Weekly FT King/Queen",
                "hot_hand_weekly": "🔥 Hot Hand Weekly",
                "clutch_man": "⏰ Clutch-man",
                "trigger_finger": "🎯 Trigger Finger",
                "weekly_whiffer": "😅 Weekly Whiffer",
            }

            for award_key, season_results in results.items():
                if award_type and award_key != award_type:
                    continue

                display_name = award_names.get(award_key, award_key)
                typer.echo(f"\n📊 {display_name}:")

                for season_key, count in sorted(season_results.items()):
                    typer.echo(f"   {season_key}: {count} awards")

            # Calculate totals
            if award_type:
                total_awards = sum(results.get(award_type, {}).values())
                typer.echo(f"\n🏆 Total {award_names.get(award_type, award_type)} awards: {total_awards}")
            else:
                total_awards = sum(sum(season_results.values()) for season_results in results.values())
                typer.echo(f"\n🏆 Total weekly awards given: {total_awards}")
        else:
            typer.echo("ℹ️  No awards were given (no games found or no player stats)")

    except Exception as e:
        typer.echo(f"❌ Error calculating weekly awards: {str(e)}", err=True)
        raise typer.Exit(1) from e


@cli.command("calculate-all-awards")
def calculate_all_awards(
    season: str = typer.Option(
        None,
        "--season",
        help="Calculates and awards weekly and season awards. If --recalculate is used, "
        "recalculates current season for season awards, all seasons for weekly awards.",
    ),
    recalculate: bool = typer.Option(
        False, "--recalculate", help="Reset existing awards and recalculate from scratch."
    ),
):
    """
    Calculate all awards - both weekly and season awards.

    Examples:
        basketball-stats calculate-all-awards                    # Calculate all awards
        basketball-stats calculate-all-awards --season 2024     # Calculate all awards for 2024
        basketball-stats calculate-all-awards --recalculate     # Reset and recalculate all
    """
    from app.config_data.awards import SEASON_AWARDS, WEEKLY_AWARDS
    from app.dependencies import get_db
    from app.services.awards_service import calculate_all_season_awards, calculate_all_weekly_awards, get_current_season

    db_session = next(get_db())

    try:
        # Validate season format if provided
        if season and not season.isdigit():
            typer.echo(f"Error: Season must be a 4-digit year (e.g., '2024'), got: {season}", err=True)
            raise typer.Exit(1)

        if recalculate:
            typer.echo("⚠️  Recalculating ALL awards (this will reset existing awards)")

        current_season = get_current_season()
        typer.echo("🎯 Calculating all awards...")
        typer.echo(f"📅 Current season: {current_season}")

        # Calculate season awards
        season_target = season or current_season
        typer.echo(f"\n🏆 Calculating season awards for {season_target}...")
        season_results = calculate_all_season_awards(db_session, season=season_target, recalculate=recalculate)

        # Calculate weekly awards
        weekly_target = season  # None means all seasons for weekly
        typer.echo(f"\n📅 Calculating weekly awards for {weekly_target or 'all seasons'}...")
        weekly_results = calculate_all_weekly_awards(db_session, season=weekly_target, recalculate=recalculate)

        # Display results
        typer.echo("\n✅ All awards calculated successfully!")

        # Display season awards
        if season_results:
            typer.echo(f"\n🏆 Season awards for {season_target}:")
            season_total = 0
            for award_type, season_data in season_results.items():
                display_name = SEASON_AWARDS.get(award_type, {}).get("name", award_type)
                count = season_data.get(season_target, 0)
                season_total += count
                typer.echo(f"   {display_name}: {count} awards")
            typer.echo(f"   Total: {season_total} season awards")

        # Display weekly awards
        if weekly_results:
            typer.echo(f"\n📅 Weekly awards for {weekly_target or 'all seasons'}:")
            weekly_total = 0
            for award_type, season_data in weekly_results.items():
                display_name = WEEKLY_AWARDS.get(award_type, {}).get("name", award_type)
                count = sum(season_data.values())  # Sum across all weeks for this award type
                weekly_total += count
                typer.echo(f"   {display_name}: {count} awards")
            typer.echo(f"   Total: {weekly_total} weekly awards")

        grand_total = sum(sum(s.values()) for s in season_results.values()) + sum(
            sum(s.values()) for s in weekly_results.values()
        )
        typer.echo(f"\n🎉 Grand total: {grand_total} awards given!")

    except Exception as e:
        typer.echo(f"❌ Error calculating all awards: {str(e)}", err=True)
        raise typer.Exit(1) from e


@cli.command("finalize-season")
def finalize_season(
    season: str = typer.Argument(..., help="Season to finalize (e.g., '2024')"),
):
    """
    Mark all season awards as finalized for a given season.

    Examples:
        basketball-stats finalize-season 2024     # Finalize 2024 season awards
    """
    from app.dependencies import get_db
    from app.services.season_awards_service import finalize_season_awards

    db_session = next(get_db())

    try:
        # Validate season format
        if not season.isdigit():
            typer.echo(f"Error: Season must be a 4-digit year (e.g., '2024'), got: {season}", err=True)
            raise typer.Exit(1)

        typer.echo(f"🏁 Finalizing season awards for {season}...")

        finalized_count = finalize_season_awards(db_session, season)

        if finalized_count > 0:
            typer.echo(f"✅ Finalized {finalized_count} season awards for {season}")
        else:
            typer.echo(f"ℹ️  No season awards to finalize for {season}")

    except Exception as e:
        typer.echo(f"❌ Error finalizing season: {str(e)}", err=True)
        raise typer.Exit(1) from e


if __name__ == "__main__":
    cli()
