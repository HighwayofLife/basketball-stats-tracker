"""Report-related CLI command handlers."""

import csv

import typer
from tabulate import tabulate  # type: ignore

from app.data_access.database_manager import db_manager
from app.services.cli_commands.report_utils import display_report_console, write_report_to_csv
from app.services.report_service import ReportService


class ReportCommands:
    """Handles report-related CLI commands."""

    @staticmethod
    def generate_report(
        game_id: int,
        report_type: str = "box-score",
        player_id: int | None = None,
        team_id: int | None = None,
        show_options: bool = False,
        output_format: str = "console",
        output_file: str | None = None,
    ) -> None:
        """
        Generate a statistical report for a specific game.

        Args:
            game_id: ID of the game to generate the report for
            report_type: Type of report to generate
            player_id: Player ID (required for player-performance report)
            team_id: Team ID (required for team-efficiency and scoring-analysis reports)
            show_options: Show available reports and parameters for a game
            output_format: Output format: console or csv
            output_file: File path for output when using csv format
        """
        report_service = ReportService()

        with db_manager.get_db_session() as db_session:
            try:
                # If --show-options flag is set, show available reports for this game
                if show_options:
                    game, suggestions = report_service.get_game_or_suggestions(db_session, game_id)
                    if not game:
                        typer.echo(f"Error: Game ID {game_id} not found.")
                        if suggestions:
                            typer.echo("\nAvailable games:")
                            for s in suggestions:
                                typer.echo(f"  ID {s['id']}: {s['date']} - {s['info']} ({s['status']})")
                            if len(suggestions) == 5:
                                typer.echo("  ... and more games")
                        typer.echo("\nUse 'basketball-stats list-games' to see all available games.")
                        return

                    options = report_service.get_report_options(db_session, game_id, game)
                    ReportCommands._show_report_options_formatted(options)
                    return

                # Generate the report
                success, report_data, error_msg = report_service.generate_game_report(
                    db_session, game_id, report_type, player_id, team_id
                )

                if not success:
                    typer.echo(f"Error: {error_msg}")

                    # Show additional help based on report data
                    if report_data:
                        if "suggestions" in report_data:
                            typer.echo("\nAvailable games:")
                            for s in report_data["suggestions"]:
                                typer.echo(f"  ID {s['id']}: {s['date']} - {s['info']} ({s['status']})")
                            typer.echo("\nUse 'basketball-stats list-games' to see all available games.")
                        elif "teams" in report_data:
                            typer.echo("\nTeams that played in this game:")
                            for team in report_data["teams"]:
                                typer.echo(f"  - {team.name} (ID: {team.id})")
                        elif "available_types" in report_data:
                            typer.echo("\nAvailable report types:")
                            for rt in report_data["available_types"]:
                                typer.echo(f"  - {rt}")
                    else:
                        # Provide context-specific help
                        if "player-performance" in report_type:
                            typer.echo(
                                f"\nUse 'basketball-stats report --id {game_id} --show-options' "
                                "to see available players."
                            )
                        elif "not been played" in error_msg:
                            typer.echo("\nThis might happen if:")
                            typer.echo("  - The game has not been played yet")
                            typer.echo("  - No statistics have been imported for this game")
                            typer.echo("\nUse 'basketball-stats import-game' to import game statistics.")
                    return

                # Extract game from report data for output
                game = report_data.pop("_game", None)
                report_type_internal = report_data.pop("_report_type", report_type)

                # Output the report in the requested format
                if game:
                    ReportCommands._output_report(
                        report_data, report_type_internal, game, output_format, output_file, game_id
                    )
                else:
                    typer.echo("Error: Unable to generate report due to missing game data.")

            except (ValueError, KeyError, TypeError) as e:
                typer.echo(f"Data error occurred: {e}")
                typer.echo("\nThis might be due to incomplete or corrupted game data.")
                typer.echo(
                    f"Try using 'basketball-stats report --id {game_id} --show-options' to see what's available."
                )
            except FileNotFoundError as e:
                typer.echo(f"File error: {e}")
            except ImportError as e:
                typer.echo(f"Module import error: {e}")
            except Exception as e:  # pylint: disable=broad-except
                typer.echo(f"Unexpected error: {e}")
                typer.echo("Please report this issue with the steps to reproduce it")

    @staticmethod
    def generate_season_report(
        season: str | None = None,
        report_type: str = "standings",
        stat_category: str = "ppg",
        player_id: int | None = None,
        team_id: int | None = None,
        limit: int = 10,
        min_games: int = 1,
        output_format: str = "console",
        output_file: str | None = None,
    ) -> None:
        """
        Generate season-long statistical reports.

        Args:
            season: Season to generate report for (e.g., '2024-2025')
            report_type: Type of report to generate
            stat_category: Stat category for player-leaders
            player_id: Player ID (required for player-season report)
            team_id: Team ID (optional for filtering)
            limit: Number of players to show in leaderboards
            min_games: Minimum games played for leaderboards
            output_format: Output format: console or csv
            output_file: File path for output when using csv format
        """
        report_service = ReportService()

        with db_manager.get_db_session() as db_session:
            try:
                # Generate the report
                success, report_data, error_msg = report_service.generate_season_report(
                    db_session, season, report_type, stat_category, player_id, team_id, limit, min_games
                )

                if not success:
                    typer.echo(f"Error: {error_msg}")
                    if report_data and "available_types" in report_data:
                        typer.echo("\nAvailable report types:")
                        for rt in report_data["available_types"]:
                            typer.echo(f"  - {rt}")
                    return

                if not report_data:
                    typer.echo(f"No data found for {report_type} report{f' for season {season}' if season else ''}")
                    return

                # Extract report type for formatting
                report_type_internal = report_data.pop("_report_type", report_type)

                # Build report title
                if report_type_internal == "standings":
                    report_title = f"Team Standings{f' - {season}' if season else ''}"
                elif report_type_internal == "player-leaders":
                    stat_name = {
                        "ppg": "Points Per Game",
                        "fpg": "Fouls Per Game",
                        "ft_pct": "Free Throw Percentage",
                        "fg_pct": "Field Goal Percentage",
                        "fg3_pct": "3-Point Percentage",
                        "efg_pct": "Effective Field Goal Percentage",
                    }.get(stat_category, stat_category)
                    report_title = f"Player Leaders - {stat_name}{f' ({season})' if season else ''}"
                elif report_type_internal == "team-stats":
                    report_title = f"Team Statistics{f' - {season}' if season else ''}"
                elif report_type_internal == "player-season":
                    if report_data.get("player"):
                        player_name = report_data["player"]["name"]
                        report_title = f"{player_name} - Season Statistics{f' ({season})' if season else ''}"
                    else:
                        report_title = f"Player Season Statistics{f' ({season})' if season else ''}"
                else:
                    report_title = f"{report_type_internal.replace('-', ' ').title()}{f' - {season}' if season else ''}"

                # Output the report in the requested format
                if output_format == "console":
                    typer.echo(f"\n{report_title}")
                    typer.echo("=" * len(report_title))

                    # Format data based on report type
                    if report_type_internal == "standings" and "standings" in report_data:
                        typer.echo(tabulate(report_data["standings"], headers="keys", tablefmt="grid", floatfmt=".3f"))
                    elif report_type_internal == "player-leaders" and "leaders" in report_data:
                        typer.echo(tabulate(report_data["leaders"], headers="keys", tablefmt="grid", floatfmt=".3f"))
                    elif report_type_internal == "team-stats" and "team_stats" in report_data:
                        typer.echo(tabulate(report_data["team_stats"], headers="keys", tablefmt="grid", floatfmt=".3f"))
                    elif report_type_internal == "player-season":
                        if "player" in report_data:
                            typer.echo(f"\nPlayer: {report_data['player']['name']}")
                            typer.echo(f"Team: {report_data['player']['team']}")
                            typer.echo(f"Jersey: #{report_data['player']['jersey']}")
                            typer.echo(f"Position: {report_data['player']['position']}")
                            typer.echo("\nSeason Statistics:")
                        if "stats" in report_data:
                            stats_table = []
                            for key, value in report_data["stats"].items():
                                stat_name = key.replace("_", " ").title()
                                stats_table.append({"Stat": stat_name, "Value": value})
                            typer.echo(tabulate(stats_table, headers="keys", tablefmt="grid"))

                elif output_format == "csv":
                    csv_file_name = output_file if output_file else f"season_{report_type}_{season or 'current'}.csv"
                    with open(csv_file_name, "w", newline="", encoding="utf-8") as csvfile:
                        # Extract the data list from report_data
                        data_list = None
                        if report_type_internal == "standings" and "standings" in report_data:
                            data_list = report_data["standings"]
                        elif report_type_internal == "player-leaders" and "leaders" in report_data:
                            data_list = report_data["leaders"]
                        elif report_type_internal == "team-stats" and "team_stats" in report_data:
                            data_list = report_data["team_stats"]
                        elif report_type_internal == "player-season" and "stats" in report_data:
                            # Convert stats dict to list format for CSV
                            player_info = report_data.get("player", {})
                            stats = report_data["stats"]
                            data_list = [
                                {
                                    "player_name": player_info.get("name", ""),
                                    "team": player_info.get("team", ""),
                                    "season": report_data.get("season", ""),
                                    **stats,
                                }
                            ]

                        if data_list and isinstance(data_list, list) and len(data_list) > 0:
                            writer = csv.DictWriter(csvfile, fieldnames=data_list[0].keys())
                            writer.writeheader()
                            writer.writerows(data_list)
                    typer.echo(f"Report generated: {csv_file_name}")
                else:
                    typer.echo(f"Unsupported format: {output_format}. Choose 'console' or 'csv'.")

            except Exception as e:  # pylint: disable=broad-except
                typer.echo(f"Error generating season report: {e}")
                typer.echo("Please check that the database has been initialized and contains data.")

    @staticmethod
    def _show_report_options_formatted(options):
        """Show formatted report options for a game."""
        game = options["game"]
        game_desc = f"{game['playing_team']} vs {game['opponent_team']}, {game['date']}"
        typer.echo(f"\nAvailable reports for Game {game['id']} ({game_desc}):")

        for report in options["available_reports"]:
            requires = (
                f" (requires --{report.get('requires')})"
                if report.get("requires")
                else " (no additional parameters required)"
            )
            typer.echo(f"  - {report['type']}{requires}")

        if not options["has_stats"]:
            typer.echo("\nNote: No statistics have been imported for this game yet.")
            typer.echo("Use 'basketball-stats import-game' to import game statistics.")
            return

        # Show available players
        if options["players"]:
            typer.echo("\nAvailable players:")
            for team_name, players in options["players"].items():
                if players:
                    typer.echo(f"  {team_name}:")
                    for player in sorted(players, key=lambda x: x["name"]):
                        typer.echo(f"    - {player['name']} #{player['jersey']} (ID: {player['id']})")

        # Show available teams
        typer.echo("\nAvailable teams:")
        for team in options["teams"]:
            typer.echo(f"  - {team['name']} (ID: {team['id']})")

    @staticmethod
    def _show_report_options(db_session, game_id, game):
        """Legacy method for backward compatibility."""
        from app.data_access.crud.crud_player_game_stats import get_player_game_stats_by_game

        game_desc = f"{game.playing_team.name} vs {game.opponent_team.name}, {game.date}"
        typer.echo(f"\nAvailable reports for Game {game_id} ({game_desc}):")
        typer.echo("  - box-score (no additional parameters required)")
        typer.echo("  - player-performance (requires --player)")
        typer.echo("  - team-efficiency (requires --team)")
        typer.echo("  - scoring-analysis (requires --team)")
        typer.echo("  - game-flow (no additional parameters required)")

        # Show available players for this game
        player_stats = get_player_game_stats_by_game(db_session, game_id)
        if player_stats:
            typer.echo("\nAvailable players:")
            players_by_team = {}
            for ps in player_stats:
                team_name = ps.player.team.name
                if team_name not in players_by_team:
                    players_by_team[team_name] = []
                players_by_team[team_name].append((ps.player.id, ps.player.name))

            for team_name, players in players_by_team.items():
                typer.echo(f"  {team_name}:")
                for pid, pname in sorted(players, key=lambda x: x[1]):
                    typer.echo(f"    - {pname} (ID: {pid})")

        typer.echo("\nAvailable teams:")
        typer.echo(f"  - {game.playing_team.name} (ID: {game.playing_team_id})")
        typer.echo(f"  - {game.opponent_team.name} (ID: {game.opponent_team_id})")

    @staticmethod
    def _output_report(report_data, report_type, game, output_format, output_file, game_id):
        """Output the report in the requested format."""
        if output_format == "console":
            typer.echo(f"\n{report_type.replace('-', ' ').title()} Report")
            typer.echo(f"Game: {game.playing_team.name} vs {game.opponent_team.name} ({game.date})")
            typer.echo("=" * 60)

            if report_type == "box-score":
                # Box score has special formatting with player stats and game summary
                if report_data["player_stats"]:
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
                display_report_console(report_data)

        elif output_format == "csv":
            csv_file_name = output_file if output_file else f"game_{game_id}_{report_type}.csv"
            with open(csv_file_name, "w", newline="", encoding="utf-8") as csvfile:
                if (
                    report_type == "box-score"
                    and report_data.get("player_stats")
                    and isinstance(report_data["player_stats"], list)
                    and len(report_data["player_stats"]) > 0
                ):
                    writer = csv.DictWriter(csvfile, fieldnames=report_data["player_stats"][0].keys())
                    writer.writeheader()
                    writer.writerows(report_data["player_stats"])
                else:
                    write_report_to_csv(report_data, csvfile)

            typer.echo(f"Report generated: {csv_file_name}")
        else:
            typer.echo(f"Unsupported format: {output_format}. Choose 'console' or 'csv'.")
