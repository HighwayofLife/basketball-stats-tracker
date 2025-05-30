"""Data validation for CSV imports."""

from typing import Any

import typer
from pydantic import ValidationError

from app.config import SHOT_MAPPING
from app.schemas.csv_schemas import GameInfoSchema, GameStatsCSVInputSchema, PlayerStatsRowSchema
from app.utils.input_parser import parse_quarter_shot_string


class DataValidator:
    """Handles validation of CSV data for imports."""

    @staticmethod
    def validate_game_stats_data(
        game_info_data: dict[str, str], player_stats_header: list[str], player_stats_rows: list[list[str]]
    ) -> GameStatsCSVInputSchema | None:
        """Validate game statistics data from CSV.

        Args:
            game_info_data: Dictionary containing game information
            player_stats_header: List of column headers
            player_stats_rows: List of player statistics rows

        Returns:
            Validated GameStatsCSVInputSchema or None if validation fails
        """
        try:
            # Map CSV fields to schema fields
            mapped_game_info = {
                "HomeTeam": game_info_data.get("Home", ""),
                "VisitorTeam": game_info_data.get("Visitor", ""),
                "Date": game_info_data.get("Date", ""),
            }

            # Validate game info
            game_info = GameInfoSchema(**mapped_game_info)

            # Validate player stats
            player_stats = []
            for row in player_stats_rows:
                player_data = DataValidator._extract_player_data_from_row(row, player_stats_header)
                if player_data:
                    try:
                        # Map extracted fields to schema fields
                        mapped_player_data = {
                            "TeamName": player_data.get("team_name", ""),
                            "PlayerJersey": player_data.get("jersey_number", ""),
                            "PlayerName": player_data.get("player_name", ""),
                            "Fouls": int(player_data.get("fouls", 0)) if player_data.get("fouls") else 0,
                            "QT1Shots": player_data.get("quarter_1", ""),
                            "QT2Shots": player_data.get("quarter_2", ""),
                            "QT3Shots": player_data.get("quarter_3", ""),
                            "QT4Shots": player_data.get("quarter_4", ""),
                        }
                        validated_player = PlayerStatsRowSchema(**mapped_player_data)
                        player_stats.append(validated_player)
                    except ValidationError as e:
                        typer.echo(f"Warning: Invalid player data - {e}")
                        continue

            if not player_stats:
                typer.echo("Error: No valid player statistics found.")
                return None

            return GameStatsCSVInputSchema(game_info=game_info, player_stats=player_stats)

        except ValidationError as e:
            typer.echo(f"Validation error: {e}")
            return None

    @staticmethod
    def _extract_player_data_from_row(row: list[str], header: list[str]) -> dict[str, Any] | None:
        """Extract player data from a CSV row.

        Args:
            row: List of values from CSV row
            header: List of column headers

        Returns:
            Dictionary of player data or None if extraction fails
        """
        if len(row) < len(header):
            return None

        player_data = {}

        # Map headers to row values
        for i, col in enumerate(header):
            value = row[i].strip() if i < len(row) else ""

            if col.lower() == "team":
                player_data["team_name"] = value
            elif col.lower() in ["player", "player name"]:
                player_data["player_name"] = value
            elif col.lower() in ["jersey", "jersey number", "#"]:
                try:
                    # Store jersey number as string but validate it can be parsed as int
                    jersey_num = str(int(value))
                    player_data["jersey_number"] = jersey_num
                except (ValueError, TypeError):
                    typer.echo(f"Warning: Invalid jersey number '{value}'. Skipping player.")
                    return None
            elif col.lower() == "fouls":
                player_data["fouls"] = value
            elif col.lower().startswith("q") and col[1:].isdigit():
                # This is a quarter column (Q1, Q2, etc.)
                quarter_num = int(col[1:])
                player_data[f"quarter_{quarter_num}"] = value
            elif col.lower() in ["ot", "overtime"]:
                player_data["overtime"] = value

        # Validate required fields
        if (
            not player_data.get("team_name")
            or not player_data.get("player_name")
            or not player_data.get("jersey_number")
        ):
            return None

        return player_data

    @staticmethod
    def validate_shot_string(shot_string: str, quarter: int, player_name: str) -> dict[str, int] | None:
        """Validate and parse a shot string.

        Args:
            shot_string: The shot string to validate (e.g., "22-1x")
            quarter: The quarter number
            player_name: The player's name (for error messages)

        Returns:
            Dictionary of shot statistics or None if validation fails
        """
        try:
            shot_stats = parse_quarter_shot_string(shot_string, shot_mapping=SHOT_MAPPING)
            return shot_stats
        except ValueError as e:
            typer.echo(f"Warning: Invalid shot string '{shot_string}' for {player_name} in Q{quarter}: {e}")
            return None
