"""CSV parsing functionality for basketball stats imports."""

import csv
from pathlib import Path
from typing import Any

import typer


class CSVParser:
    """Handles CSV file parsing for roster and game stats imports."""

    @staticmethod
    def check_file_exists(file_path: str) -> Path | None:
        """Check if the given file exists.

        Args:
            file_path: Path to the file to check

        Returns:
            Path object if file exists, None otherwise
        """
        path = Path(file_path)
        if not path.exists():
            typer.echo(f"Error: File '{file_path}' not found.")
            return None
        return path

    @staticmethod
    def read_roster_csv(roster_path: Path) -> tuple[dict[str, dict[str, int]], list[dict[str, Any]]]:
        """Read and parse roster CSV file.

        Args:
            roster_path: Path to the roster CSV file

        Returns:
            Tuple of (team_data, player_data) dictionaries

        Raises:
            csv.Error: If CSV parsing fails
            ValueError: If required fields are missing
        """
        team_data = {}
        player_data = []

        with open(roster_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            required_fields = ["team_name", "player_name", "jersey_number"]
            missing_fields = [field for field in required_fields if field not in (reader.fieldnames or [])]

            if missing_fields:
                raise ValueError(f"CSV file missing required headers: {', '.join(missing_fields)}")

            for row in reader:
                team_name = row["team_name"].strip()
                player_name = row["player_name"].strip()

                try:
                    jersey_number = str(int(row["jersey_number"]))  # Validate as int, store as string
                except (ValueError, TypeError):
                    typer.echo(
                        f"Warning: Invalid jersey number '{row['jersey_number']}' for player '{player_name}'. Skipping."
                    )
                    continue

                if team_name not in team_data:
                    team_data[team_name] = {"player_count": 0}
                team_data[team_name]["player_count"] += 1

                player_info = {
                    "team_name": team_name,
                    "name": player_name,
                    "jersey_number": jersey_number,
                }

                # Optional fields
                if "position" in row:
                    player_info["position"] = row["position"].strip()
                if "height" in row:
                    player_info["height"] = row["height"].strip()
                if "weight" in row:
                    player_info["weight"] = row["weight"].strip()
                if "year" in row:
                    player_info["year"] = row["year"].strip()

                player_data.append(player_info)

        return team_data, player_data

    @staticmethod
    def read_game_stats_csv(game_stats_path: Path) -> tuple[dict[str, str], list[str], list[list[str]]] | None:
        """Read and parse a game stats CSV file into sections.

        Args:
            game_stats_path: Path to the game stats CSV file

        Returns:
            Tuple of (game_info_data, player_stats_header, player_stats_rows) or None on error
        """
        with open(game_stats_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)

            if len(rows) < 5:  # Need at least 5 rows (home, visitor, date, header, 1 player)
                typer.echo("Error: CSV file doesn't have enough rows.")
                return None

            # Parse new simplified format
            # Row 0: Home,<team_name>
            # Row 1: Visitor/Away,<team_name>
            # Row 2: Date,<date>
            # Row 3: Headers
            # Row 4+: Player data

            game_info_data = {}

            # Parse home team (row 0)
            if len(rows[0]) >= 2 and rows[0][0].lower() == "home":
                game_info_data["Home"] = rows[0][1].strip()
            else:
                typer.echo("Error: First row should be 'Home,<team_name>'")
                return None

            # Parse visitor team (row 1)
            if len(rows[1]) >= 2 and rows[1][0].lower() in ["visitor", "away"]:
                game_info_data["Visitor"] = rows[1][1].strip()
            else:
                typer.echo("Error: Second row should be 'Visitor,<team_name>' or 'Away,<team_name>'")
                return None

            # Parse date (row 2)
            if len(rows[2]) >= 2 and rows[2][0].lower() == "date":
                game_info_data["Date"] = rows[2][1].strip()
            else:
                typer.echo("Error: Third row should be 'Date,<date>'")
                return None

            # Headers are in row 3
            player_stats_header = rows[3]

            # Player data starts from row 4
            player_stats_rows = rows[4:]

            # Filter out empty rows
            player_stats_rows = [row for row in player_stats_rows if any(cell.strip() for cell in row)]

            if not player_stats_rows:
                typer.echo("Error: No player statistics found in CSV file.")
                return None

            return game_info_data, player_stats_header, player_stats_rows
