"""Listing-related CLI command handlers."""

import csv
from datetime import datetime
from typing import Any

import typer
from tabulate import tabulate  # type: ignore

from app.data_access.crud.crud_game import get_all_games
from app.data_access.crud.crud_player import get_all_players
from app.data_access.crud.crud_team import get_all_teams
from app.data_access.database_manager import db_manager


def _output_data_as_table_or_csv(
    data: list[dict[str, Any]],
    output_format: str,
    output_file: str | None,
    default_csv_name: str,
    entity_name: str,
    console_message: str | None = None,
) -> None:
    """
    Helper function to output data as either console table or CSV file.

    Args:
        data: List of dictionaries containing the data to output
        output_format: Either "console" or "csv"
        output_file: Optional file path for CSV output
        default_csv_name: Default filename if output_file is not provided
        entity_name: Name of entities being listed (e.g., "game", "player", "team")
        console_message: Optional additional message to show in console output
    """
    if not data:
        typer.echo(f"No {entity_name}s found matching the criteria.")
        return

    if output_format == "console":
        typer.echo(f"\nFound {len(data)} {entity_name}(s)")
        typer.echo("=" * 60)
        typer.echo(tabulate(data, headers="keys", tablefmt="grid"))
        if console_message:
            typer.echo(f"\n{console_message}")

    elif output_format == "csv":
        csv_file_name = output_file if output_file else default_csv_name
        with open(csv_file_name, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        typer.echo(f"{entity_name.capitalize()}s list exported to: {csv_file_name}")

    else:
        typer.echo(f"Unsupported format: {output_format}. Choose 'console' or 'csv'.")


def _handle_format_validation(output_format: str) -> bool:
    """
    Validate output format and show error if invalid.

    Args:
        output_format: The format to validate

    Returns:
        True if format is valid, False otherwise
    """
    if output_format not in ["console", "csv"]:
        typer.echo(f"Unsupported format: {output_format}. Choose 'console' or 'csv'.")
        return False
    return True


class ListingCommands:
    """Handles listing-related CLI commands."""

    @staticmethod
    def list_games(
        team: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        season: str | None = None,
        detailed: bool = False,
        output_format: str = "console",
        output_file: str | None = None,
    ) -> None:
        """
        List all games with optional filtering.

        Args:
            team: Filter by team name (home or away)
            from_date: Filter by start date (YYYY-MM-DD)
            to_date: Filter by end date (YYYY-MM-DD)
            season: Filter by season (e.g., '2024-2025')
            detailed: Show more details
            output_format: Output format: console or csv
            output_file: File path for CSV output
        """
        with db_manager.get_db_session() as db_session:
            try:
                # Get all games
                games = get_all_games(db_session)

                # Apply filters
                filtered_games = []
                for game in games:
                    # Team filter
                    if team:
                        team_lower = team.lower()
                        if not (
                            team_lower in game.playing_team.name.lower()
                            or team_lower in game.opponent_team.name.lower()
                        ):
                            continue

                    # Date filters
                    if from_date:
                        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                        if game.date < from_dt:
                            continue

                    if to_date:
                        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                        if game.date > to_dt:
                            continue

                    # Season filter (assuming season format is "YYYY-YYYY")
                    if season:
                        season_parts = season.split("-")
                        if len(season_parts) == 2:
                            season_start = int(season_parts[0])
                            season_end = int(season_parts[1])
                            game_year = game.date.year
                            game_month = game.date.month
                            # Season typically runs from October to April
                            if game_month >= 10:  # Oct-Dec
                                if game_year != season_start:
                                    continue
                            else:  # Jan-Apr
                                if game_year != season_end:
                                    continue

                    filtered_games.append(game)

                # Sort games by date
                filtered_games.sort(key=lambda g: g.date, reverse=True)

                # Format data for display
                output_data = []
                for game in filtered_games:
                    # Check if game has been played by looking for player stats
                    from app.data_access.crud.crud_player_game_stats import get_player_game_stats_by_game

                    game_stats = get_player_game_stats_by_game(db_session, game.id)
                    if game_stats:
                        # Calculate scores from player stats
                        playing_team_score = 0
                        opponent_team_score = 0
                        for pgs in game_stats:
                            # Get quarter stats to calculate total points
                            from app.data_access.crud.crud_player_quarter_stats import get_player_quarter_stats

                            quarter_stats = get_player_quarter_stats(db_session, pgs.id)
                            player_points = 0
                            for qs in quarter_stats:
                                player_points += (qs.ftm or 0) + (qs.fg2m or 0) * 2 + (qs.fg3m or 0) * 3

                            # Add to appropriate team total
                            if pgs.player.team_id == game.playing_team_id:
                                playing_team_score += player_points
                            else:
                                opponent_team_score += player_points

                        score = f"{playing_team_score}-{opponent_team_score}"
                        status = "Complete"
                    else:
                        score = "--"
                        status = "Scheduled"

                    row = {
                        "ID": game.id,
                        "Date": game.date.strftime("%Y-%m-%d"),
                        "Home Team": game.playing_team.name,
                        "Away Team": game.opponent_team.name,
                        "Score": score,
                        "Status": status,
                    }

                    if detailed and status == "Complete":
                        # Add more details
                        # Parse scores from the score string
                        scores = score.split("-")
                        if len(scores) == 2:
                            playing_score = int(scores[0])
                            opponent_score = int(scores[1])
                            if playing_score > opponent_score:
                                winner = game.playing_team.name
                            else:
                                winner = game.opponent_team.name
                            row["Winner"] = winner
                            row["Margin"] = abs(playing_score - opponent_score)

                    output_data.append(row)

                # Output using helper function
                _output_data_as_table_or_csv(
                    data=output_data,
                    output_format=output_format,
                    output_file=output_file,
                    default_csv_name="games_list.csv",
                    entity_name="game",
                    console_message="Use 'basketball-stats report --id <ID>' to generate reports for a specific game.",
                )

            except ValueError as e:
                typer.echo(f"Error parsing date: {e}")
                typer.echo("Please use YYYY-MM-DD format for dates.")
            except Exception as e:  # pylint: disable=broad-except
                typer.echo(f"Error listing games: {e}")

    @staticmethod
    def list_players(
        team: str | None = None,
        name: str | None = None,
        position: str | None = None,
        output_format: str = "console",
        output_file: str | None = None,
    ) -> None:
        """
        List all players with optional filtering.

        Args:
            team: Filter by team name
            name: Search by player name (partial match)
            position: Filter by position
            output_format: Output format: console or csv
            output_file: File path for CSV output
        """
        with db_manager.get_db_session() as db_session:
            try:
                # Get all players
                players = get_all_players(db_session)

                # Apply filters
                filtered_players = []
                for player in players:
                    # Team filter
                    if team and team.lower() not in player.team.name.lower():
                        continue

                    # Name filter (partial match)
                    if name and name.lower() not in player.name.lower():
                        continue

                    # Position filter
                    if position and player.position != position.upper():
                        continue

                    filtered_players.append(player)

                # Sort players by team and then by name
                filtered_players.sort(key=lambda p: (p.team.name, p.name))

                # Format data for display
                output_data = []
                for player in filtered_players:
                    row = {
                        "ID": player.id,
                        "Name": player.name,
                        "Team": player.team.name,
                        "Jersey #": player.jersey_number,
                        "Position": player.position,
                    }

                    # Add optional fields if they exist
                    if player.height:
                        row["Height"] = player.height
                    if player.weight:
                        row["Weight"] = player.weight
                    if player.year:
                        row["Year"] = player.year

                    output_data.append(row)

                # Output using helper function
                _output_data_as_table_or_csv(
                    data=output_data,
                    output_format=output_format,
                    output_file=output_file,
                    default_csv_name="players_list.csv",
                    entity_name="player",
                    console_message="Use player IDs with report commands to generate player-specific reports.",
                )

            except Exception as e:  # pylint: disable=broad-except
                typer.echo(f"Error listing players: {e}")

    @staticmethod
    def list_teams(
        with_players: bool = False,
        output_format: str = "console",
        output_file: str | None = None,
    ) -> None:
        """
        List all teams.

        Args:
            with_players: Show team rosters
            output_format: Output format: console or csv
            output_file: File path for CSV output
        """
        with db_manager.get_db_session() as db_session:
            try:
                # Get all teams
                teams = get_all_teams(db_session)

                if not teams:
                    typer.echo("No teams found in the database.")
                    return

                # Sort teams by name
                teams.sort(key=lambda t: t.name)

                # Format data for display
                if with_players:
                    # Show detailed view with rosters
                    if output_format == "console":
                        typer.echo(f"\nFound {len(teams)} team(s)")
                        typer.echo("=" * 60)

                        for team in teams:
                            typer.echo(f"\n{team.name} (ID: {team.id})")
                            typer.echo("-" * len(f"{team.name} (ID: {team.id})"))

                            if team.players:
                                player_data = []
                                for player in sorted(team.players, key=lambda p: p.jersey_number):
                                    player_data.append(
                                        {
                                            "Jersey #": player.jersey_number,
                                            "Name": player.name,
                                            "Position": player.position,
                                            "ID": player.id,
                                        }
                                    )
                                typer.echo(tabulate(player_data, headers="keys", tablefmt="simple"))
                            else:
                                typer.echo("  No players on roster")

                    elif output_format == "csv":
                        # For CSV with players, create a flat structure
                        output_data = []
                        for team in teams:
                            if team.players:
                                for player in team.players:
                                    output_data.append(
                                        {
                                            "Team ID": team.id,
                                            "Team Name": team.name,
                                            "Player ID": player.id,
                                            "Player Name": player.name,
                                            "Jersey #": player.jersey_number,
                                            "Position": player.position,
                                        }
                                    )
                            else:
                                # Include teams with no players
                                output_data.append(
                                    {
                                        "Team ID": team.id,
                                        "Team Name": team.name,
                                        "Player ID": "",
                                        "Player Name": "",
                                        "Jersey #": "",
                                        "Position": "",
                                    }
                                )

                        csv_file_name = output_file if output_file else "teams_with_rosters.csv"
                        if output_data:  # Only write if there's data
                            with open(csv_file_name, "w", newline="", encoding="utf-8") as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=output_data[0].keys())
                                writer.writeheader()
                                writer.writerows(output_data)
                            typer.echo(f"Teams with rosters exported to: {csv_file_name}")
                        else:
                            typer.echo("No team data to export.")

                else:
                    # Simple team list
                    output_data = []
                    for team in teams:
                        output_data.append(
                            {
                                "ID": team.id,
                                "Name": team.name,
                                "Player Count": len(team.players),
                            }
                        )

                    # Output using helper function
                    _output_data_as_table_or_csv(
                        data=output_data,
                        output_format=output_format,
                        output_file=output_file,
                        default_csv_name="teams_list.csv",
                        entity_name="team",
                        console_message=(
                            "Use team IDs with report commands to generate team-specific reports.\\n"
                            "Add --with-players to see team rosters."
                        ),
                    )

            except Exception as e:  # pylint: disable=broad-except
                typer.echo(f"Error listing teams: {e}")
