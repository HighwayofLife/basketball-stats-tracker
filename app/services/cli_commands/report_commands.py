"""Report-related CLI command handlers."""

import csv

import typer
from tabulate import tabulate  # type: ignore

from app.data_access.crud import get_player_by_id, get_player_season_stats
from app.data_access.crud.crud_game import get_all_games, get_game_by_id
from app.data_access.crud.crud_player_game_stats import get_player_game_stats_by_game
from app.data_access.crud.crud_team_season_stats import get_season_teams, get_team_season_stats
from app.data_access.database_manager import db_manager
from app.reports.report_generator import ReportGenerator
from app.services.cli_commands.report_utils import display_report_console, write_report_to_csv
from app.services.season_stats_service import SeasonStatsService
from app.utils import stats_calculator
from app.utils.stats_calculator import calculate_efg, calculate_percentage


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
        with db_manager.get_db_session() as db_session:
            try:
                # First, verify the game exists
                game = get_game_by_id(db_session, game_id)
                if not game:
                    typer.echo(f"Error: Game ID {game_id} not found.")
                    typer.echo("\nAvailable games:")
                    # Show recent games to help user
                    games = get_all_games(db_session)
                    if games:
                        # Show last 5 games
                        games.sort(key=lambda g: g.date, reverse=True)
                        for g in games[:5]:
                            # Check if game has been played
                            from app.data_access.crud.crud_player_game_stats import get_player_game_stats_by_game

                            game_stats = get_player_game_stats_by_game(db_session, g.id)
                            score = "Scheduled" if not game_stats else "Played"
                            game_info = f"{g.playing_team.name} vs {g.opponent_team.name}"
                            typer.echo(f"  ID {g.id}: {g.date} - {game_info} ({score})")
                        if len(games) > 5:
                            typer.echo(f"  ... and {len(games) - 5} more games")
                    typer.echo("\nUse 'basketball-stats list-games' to see all available games.")
                    return

                # If --show-options flag is set, show available reports for this game
                if show_options:
                    ReportCommands._show_report_options(db_session, game_id, game)
                    return

                report_generator = ReportGenerator(db_session, stats_calculator)

                # Generate the appropriate report based on type
                if report_type == "box-score":
                    player_stats, game_summary = report_generator.get_game_box_score_data(game_id)
                    report_data = {"player_stats": player_stats, "game_summary": game_summary}

                elif report_type == "player-performance":
                    if not player_id:
                        typer.echo("Error: Player ID is required for player-performance report.")
                        typer.echo(
                            f"\nUse 'basketball-stats report --id {game_id} --show-options' to see available players."
                        )
                        return

                    # Verify player exists
                    player = get_player_by_id(db_session, player_id)
                    if not player:
                        typer.echo(f"Error: Player ID {player_id} not found.")
                        typer.echo("\nUse 'basketball-stats list-players' to see all available players.")
                        return

                    report_data = report_generator.generate_player_performance_report(player_id, game_id)

                elif report_type == "team-efficiency":
                    if not team_id:
                        typer.echo("Error: Team ID is required for team-efficiency report.")
                        typer.echo("\nAvailable teams for this game:")
                        typer.echo(f"  - {game.playing_team.name} (ID: {game.playing_team_id})")
                        typer.echo(f"  - {game.opponent_team.name} (ID: {game.opponent_team_id})")
                        return

                    # Verify team exists and is in this game
                    if team_id not in [game.playing_team_id, game.opponent_team_id]:
                        typer.echo(f"Error: Team ID {team_id} did not play in game {game_id}.")
                        typer.echo("\nTeams that played in this game:")
                        typer.echo(f"  - {game.playing_team.name} (ID: {game.playing_team_id})")
                        typer.echo(f"  - {game.opponent_team.name} (ID: {game.opponent_team_id})")
                        return

                    report_data = report_generator.generate_team_efficiency_report(team_id, game_id)

                elif report_type == "scoring-analysis":
                    if not team_id:
                        typer.echo("Error: Team ID is required for scoring-analysis report.")
                        typer.echo("\nAvailable teams for this game:")
                        typer.echo(f"  - {game.playing_team.name} (ID: {game.playing_team_id})")
                        typer.echo(f"  - {game.opponent_team.name} (ID: {game.opponent_team_id})")
                        return

                    # Verify team exists and is in this game
                    if team_id not in [game.playing_team_id, game.opponent_team_id]:
                        typer.echo(f"Error: Team ID {team_id} did not play in game {game_id}.")
                        typer.echo("\nTeams that played in this game:")
                        typer.echo(f"  - {game.playing_team.name} (ID: {game.playing_team_id})")
                        typer.echo(f"  - {game.opponent_team.name} (ID: {game.opponent_team_id})")
                        return

                    report_data = report_generator.generate_scoring_analysis_report(team_id, game_id)

                elif report_type == "game-flow":
                    report_data = report_generator.generate_game_flow_report(game_id)

                else:
                    typer.echo(f"Error: Unknown report type '{report_type}'")
                    typer.echo("\nAvailable report types:")
                    typer.echo("  - box-score")
                    typer.echo("  - player-performance")
                    typer.echo("  - team-efficiency")
                    typer.echo("  - scoring-analysis")
                    typer.echo("  - game-flow")
                    return

                if not report_data or (isinstance(report_data, dict) and all(not v for v in report_data.values())):
                    typer.echo(f"No data found for {report_type} report.")
                    typer.echo("\nThis might happen if:")
                    typer.echo("  - The game has not been played yet")
                    typer.echo("  - No statistics have been imported for this game")
                    typer.echo("\nUse 'basketball-stats import-game' to import game statistics.")
                    return

                # Output the report in the requested format
                ReportCommands._output_report(report_data, report_type, game, output_format, output_file, game_id)

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
                        team_stats = get_team_season_stats(db_session, team_id, season or "")
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
                        all_team_stats: list = get_season_teams(db_session, season or "")
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

                    player = get_player_by_id(db_session, player_id)
                    if not player:
                        typer.echo(f"Error: Player with ID {player_id} not found.")
                        return

                    player_stats = get_player_season_stats(db_session, player_id, season or "")
                    if player_stats:
                        total_points = (
                            player_stats.total_ftm + (player_stats.total_2pm * 2) + (player_stats.total_3pm * 3)
                        )
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

    @staticmethod
    def _show_report_options(db_session, game_id, game):
        """Show available report options for a game."""
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
