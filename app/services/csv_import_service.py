"""
Service for importing roster and game stats from CSV files.
Handles all parsing, validation, and DB operations for CSV imports.
"""

import csv
from pathlib import Path
from typing import Any, cast

import typer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.data_access.database_manager as db_manager
from app.config import SHOT_MAPPING
from app.data_access.models import Game, Player, Team
from app.schemas.csv_schemas import GameInfoSchema, GameStatsCSVInputSchema, PlayerStatsRowSchema
from app.services.game_service import GameService
from app.services.player_service import PlayerService
from app.services.stats_entry_service import StatsEntryService
from app.utils.input_parser import parse_quarter_shot_string


def _check_file_exists(file_path: str) -> Path | None:
    """
    Checks if the given file exists. Returns Path object if it does, None otherwise.
    """
    path = Path(file_path)
    if not path.exists():
        typer.echo(f"Error: File '{file_path}' not found.")
        return None
    return path


def import_roster_from_csv(roster_file: str, dry_run: bool = False) -> bool:
    """
    Import teams and players from a CSV file. Returns True on success, False on error.
    """
    roster_path = _check_file_exists(roster_file)
    if not roster_path:
        return False

    try:
        team_data, player_data = _read_and_validate_roster_csv(roster_path)
        if not team_data or not player_data:
            return False

        _display_roster_import_summary(roster_file, team_data, player_data)

        if dry_run:
            typer.echo("\nDry run mode: No changes were made to the database.")
            return True

        return _process_roster_import(team_data, player_data)
    except (FileNotFoundError, PermissionError) as e:
        typer.echo(f"File error: {e}")
        return False
    except csv.Error as e:
        typer.echo(f"CSV parsing error: {e}")
        return False
    except ValueError as e:
        typer.echo(f"Data validation error: {e}")
        return False
    except OSError as e:
        typer.echo(f"I/O error: {e}")
        return False
    except Exception as e:  # pylint: disable=broad-except
        typer.echo(f"Unexpected error importing roster: {e}")
        return False


def _read_and_validate_roster_csv(roster_path: Path) -> tuple[dict[str, dict[str, int]], list[dict[str, Any]]]:
    """
    Reads and validates the roster CSV file.
    Returns a tuple of (team_data, player_data) dictionaries.
    """
    team_data = {}
    player_data = []

    with open(roster_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        required_fields = ["team_name", "player_name", "jersey_number"]
        missing_fields = [field for field in required_fields if field not in (reader.fieldnames or [])]

        if missing_fields:
            typer.echo(f"Error: CSV file missing required headers: {', '.join(missing_fields)}")
            return {}, []

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
                team_data[team_name] = {"count": 0}
            team_data[team_name]["count"] += 1
            player_data.append({"team_name": team_name, "name": player_name, "jersey_number": jersey_number})

    return team_data, player_data


def _display_roster_import_summary(
    roster_file: str, team_data: dict[str, dict[str, int]], player_data: list[dict[str, Any]]
) -> None:
    """
    Displays a summary of the roster data being imported.
    """
    typer.echo(f"\nRoster import summary from {roster_file}:")
    typer.echo(f"Found {len(team_data)} teams and {len(player_data)} players.\n")
    for team_name, info in team_data.items():
        typer.echo(f"Team: {team_name} - {info['count']} players")


def _process_roster_import(team_data: dict[str, dict[str, int]], player_data: list[dict[str, Any]]) -> bool:
    """
    Processes the roster import by adding teams and players to the database.
    Returns True on success, False on error.
    """
    with db_manager.db_manager.get_db_session() as db:
        teams_added, teams_existing, team_name_to_id = _process_teams(db, team_data)
        players_added, players_existing, players_error = _process_players(db, player_data, team_name_to_id)

        db.commit()

        typer.echo("\nRoster import completed:")
        typer.echo(f"Teams: {teams_added} added, {teams_existing} already existed")
        typer.echo(
            f"Players: {players_added} added, {players_existing} already existed, {players_error} errors/conflicts"
        )
        return True


def _process_teams(db: Session, team_data: dict[str, dict[str, int]]) -> tuple[int, int, dict[str, int]]:
    """
    Process teams by adding new teams to the database or getting existing ones.
    Returns (teams_added, teams_existing, team_name_to_id)
    """
    teams_added = 0
    teams_existing = 0
    team_name_to_id = {}

    for team_name in team_data:
        existing_team = db.query(Team).filter(Team.name == team_name).first()
        if existing_team:
            team_name_to_id[team_name] = existing_team.id
            teams_existing += 1
        else:
            new_team = Team(name=team_name)
            db.add(new_team)
            db.flush()
            team_name_to_id[team_name] = new_team.id
            teams_added += 1

    return teams_added, teams_existing, team_name_to_id


def _process_players(
    db: Session, player_data: list[dict[str, Any]], team_name_to_id: dict[str, int]
) -> tuple[int, int, int]:
    """
    Process players by adding new players to the database or updating existing ones.
    Returns (players_added, players_existing, players_error)
    """
    players_added = 0
    players_existing = 0
    players_error = 0

    for player in player_data:
        team_id = team_name_to_id[player["team_name"]]
        existing_player = (
            db.query(Player)
            .filter(
                (Player.team_id == team_id)
                & ((Player.name == player["name"]) | (Player.jersey_number == player["jersey_number"]))
            )
            .first()
        )

        if existing_player:
            if existing_player.name == player["name"] and existing_player.jersey_number == player["jersey_number"]:
                players_existing += 1
            else:
                conflict_type = "name" if existing_player.name == player["name"] else "jersey number"
                typer.echo(
                    f"Warning: Player conflict for team '{player['team_name']}': "
                    f"'{player['name']}' (#{player['jersey_number']}) - "
                    f"A player with the same {conflict_type} already exists. Skipping."
                )
                players_error += 1
        else:
            new_player = Player(
                team_id=team_id,
                name=player["name"],
                jersey_number=player["jersey_number"],
            )
            db.add(new_player)
            players_added += 1

    return players_added, players_existing, players_error


def import_game_stats_from_csv(game_stats_file: str, dry_run: bool = False) -> bool:
    """
    Import game statistics from a CSV file. Returns True on success, False on error.
    """
    game_stats_path = _check_file_exists(game_stats_file)
    if not game_stats_path:
        return False

    try:
        # Read and parse the CSV file
        csv_sections = _read_and_parse_game_stats_csv(game_stats_path)
        if not csv_sections:
            return False

        game_info_data, player_stats_header, player_stats_rows = csv_sections

        # Validate game info
        validated_data = _validate_game_stats_data(game_info_data, player_stats_header, player_stats_rows)
        if not validated_data:
            return False

        # Display import summary
        _display_game_stats_import_summary(game_stats_file, validated_data)

        if dry_run:
            typer.echo("\nDry run mode: No changes were made to the database.")
            return True

        # Process the import
        return _process_game_stats_import(validated_data)

    except (FileNotFoundError, PermissionError) as e:
        typer.echo(f"File error: {e}")
        return False
    except csv.Error as e:
        typer.echo(f"CSV parsing error: {e}")
        return False
    except ValueError as e:
        typer.echo(f"Data validation error: {e}")
        return False
    except OSError as e:
        typer.echo(f"I/O error: {e}")
        return False
    except Exception as e:  # pylint: disable=broad-except
        typer.echo(f"Unexpected error importing game stats: {e}")
        return False


def _read_and_parse_game_stats_csv(game_stats_path: Path) -> tuple[dict[str, str], list[str], list[list[str]]] | None:
    """
    Read and parse a game stats CSV file into sections.
    Returns a tuple of (game_info_data, player_stats_header, player_stats_rows) or None on error.
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

        # Parse header (row 3)
        player_stats_header = rows[3]

        # Parse player data (rows 4+)
        player_stats_rows = []
        for row in rows[4:]:
            if row and any(cell.strip() for cell in row):  # Skip empty rows
                player_stats_rows.append(row)

        if not player_stats_rows:
            typer.echo("Error: No player data found.")
            return None

        return game_info_data, player_stats_header, player_stats_rows


def _validate_game_stats_data(
    game_info_data: dict[str, str], player_stats_header: list[str], player_stats_rows: list[list[str]]
) -> GameStatsCSVInputSchema | None:
    """
    Validates the game stats data and returns a GameStatsCSVInputSchema object if valid.
    """
    try:
        # Validate game information - now using Home/Visitor instead of Playing/Opponent
        game_info_valid = {
            "HomeTeam": game_info_data.get("Home", ""),
            "VisitorTeam": game_info_data.get("Visitor", ""),
            "Date": game_info_data.get("Date", ""),
        }
        game_info = GameInfoSchema(**game_info_valid)

        # Process and validate player stats
        player_stats = _process_player_stats_rows(player_stats_header, player_stats_rows)

        # Create the validated data object
        return GameStatsCSVInputSchema(
            game_info=game_info,
            player_stats=player_stats,
        )
    except ValueError as e:
        typer.echo(f"Error validating game information: {e}")
        return None


def _process_player_stats_rows(
    player_stats_header: list[str], player_stats_rows: list[list[str]]
) -> list[PlayerStatsRowSchema]:
    """
    Processes player stats rows into validated PlayerStatsRowSchema objects.
    """
    player_stats = []
    for i, player_row in enumerate(player_stats_rows):
        # Ensure row has the right number of elements
        if len(player_row) < len(player_stats_header):
            player_row.extend([""] * (len(player_stats_header) - len(player_row)))
        elif len(player_row) > len(player_stats_header):
            player_row = player_row[: len(player_stats_header)]

        player_dict = _extract_player_data_from_row(player_stats_header, player_row, i)

        player_stats.append(
            PlayerStatsRowSchema(
                TeamName=str(player_dict["TeamName"]),
                PlayerJersey=str(player_dict["PlayerJersey"]),
                PlayerName=str(player_dict["PlayerName"]),
                Fouls=cast(int, player_dict["Fouls"]),
                QT1Shots=str(player_dict["QT1Shots"]),
                QT2Shots=str(player_dict["QT2Shots"]),
                QT3Shots=str(player_dict["QT3Shots"]),
                QT4Shots=str(player_dict["QT4Shots"]),
            )
        )
    return player_stats


def _extract_player_data_from_row(
    player_stats_header: list[str], player_row: list[str], row_index: int
) -> dict[str, Any]:
    """
    Extracts player data from a row based on the header.
    Headers are case-insensitive and support multiple variations.
    """
    player_dict = {
        "TeamName": "",
        "PlayerJersey": "0",
        "PlayerName": "",
        "Fouls": 0,
        "QT1Shots": "",
        "QT2Shots": "",
        "QT3Shots": "",
        "QT4Shots": "",
    }

    for j, header in enumerate(player_stats_header):
        if j >= len(player_row):
            continue

        # Normalize header: lowercase and remove spaces
        header_normalized = header.lower().replace(" ", "")
        cell_value = player_row[j].strip() if player_row[j] else ""

        if header_normalized in ("teamname", "team"):
            player_dict["TeamName"] = cell_value
        elif header_normalized in ("playerjersey", "jersey", "jerseynumber", "number"):
            # Store jersey number as string to handle "0" vs "00"
            player_dict["PlayerJersey"] = cell_value.strip() if cell_value else "0"
        elif header_normalized in ("playername", "name", "player"):
            player_dict["PlayerName"] = cell_value
        elif header_normalized == "fouls":
            try:
                player_dict["Fouls"] = int(cell_value) if cell_value else 0
            except (ValueError, TypeError):
                typer.echo(f"Warning: Invalid fouls '{cell_value}' in row {row_index + 1}. Using 0.")
                player_dict["Fouls"] = 0
        elif header_normalized in ("qt1shots", "qt1"):
            player_dict["QT1Shots"] = cell_value
        elif header_normalized in ("qt2shots", "qt2"):
            player_dict["QT2Shots"] = cell_value
        elif header_normalized in ("qt3shots", "qt3"):
            player_dict["QT3Shots"] = cell_value
        elif header_normalized in ("qt4shots", "qt4"):
            player_dict["QT4Shots"] = cell_value

    return player_dict


def _display_game_stats_import_summary(game_stats_file: str, validated_data: GameStatsCSVInputSchema) -> None:
    """
    Displays a summary of the game stats being imported.
    """
    typer.echo(f"\nGame stats import summary from {game_stats_file}:")
    typer.echo(
        f"Game: {validated_data.game_info.HomeTeam} (Home) vs {validated_data.game_info.VisitorTeam} (Visitor) "
        f"on {validated_data.game_info.Date}"
    )
    typer.echo(f"Players: {len(validated_data.player_stats)}")


def _process_game_stats_import(validated_data: GameStatsCSVInputSchema) -> bool:
    """
    Processes the game stats import by adding game and player statistics to the database.
    """
    with db_manager.db_manager.get_db_session() as db:
        game_service = GameService(db)
        player_service = PlayerService(db)
        stats_entry_service = StatsEntryService(db, parse_quarter_shot_string, SHOT_MAPPING)

        # Create the game - using home team as playing team and visitor as opponent
        game = game_service.add_game(
            validated_data.game_info.Date,
            validated_data.game_info.HomeTeam,
            validated_data.game_info.VisitorTeam,
        )

        typer.echo(f"\nCreated game #{game.id}: {game.playing_team.name} vs {game.opponent_team.name} on {game.date}")

        # Process player stats
        players_processed, players_error = _record_player_stats(
            game, validated_data.player_stats, game_service, player_service, stats_entry_service, db
        )

        # Calculate and update game scores
        _update_game_scores(db, game)

        typer.echo(f"Game stats import completed: {players_processed} players processed, {players_error} errors")
        typer.echo("Import completed successfully")
        return True


def _record_player_stats(
    game: Game,
    player_stats: list[PlayerStatsRowSchema],
    game_service: GameService,
    player_service: PlayerService,
    stats_entry_service: StatsEntryService,
    db: Session | None = None,
) -> tuple[int, int]:
    """
    Records statistics for all players in a game.
    Returns (players_processed, players_error)
    """
    players_processed = 0
    players_error = 0

    for player_stat in player_stats:
        try:
            team = game_service.get_or_create_team(player_stat.TeamName)
            player = player_service.get_or_create_player(team.id, player_stat.PlayerJersey, player_stat.PlayerName)
            stats_entry_service.record_player_game_performance(
                game.id,
                player.id,
                player_stat.Fouls,
                [player_stat.QT1Shots, player_stat.QT2Shots, player_stat.QT3Shots, player_stat.QT4Shots],
            )
            players_processed += 1
        except (ValueError, KeyError, TypeError) as e:
            typer.echo(f"Data error processing player {player_stat.PlayerName}: {e}")
            players_error += 1
            # Rollback the session to recover from the error
            if db:
                db.rollback()
        except OSError as e:
            typer.echo(f"I/O error processing player {player_stat.PlayerName}: {e}")
            players_error += 1
            if db:
                db.rollback()
        except SQLAlchemyError as e:
            typer.echo(f"Database error processing player {player_stat.PlayerName}: {e}")
            players_error += 1
            # Rollback the session to recover from the error
            if db:
                db.rollback()

    return players_processed, players_error


def _update_game_scores(db: Session, game: Game) -> None:
    """Calculate and update game scores based on player statistics."""
    from app.data_access.models import Player, PlayerGameStats

    # Get all player stats for this game
    player_stats = db.query(PlayerGameStats).filter(PlayerGameStats.game_id == game.id).join(Player).all()

    playing_team_score = 0
    opponent_team_score = 0

    for stat in player_stats:
        # Calculate player's total points
        points = stat.total_ftm + (stat.total_2pm * 2) + (stat.total_3pm * 3)

        # Add to appropriate team total
        if stat.player.team_id == game.playing_team_id:
            playing_team_score += points
        elif stat.player.team_id == game.opponent_team_id:
            opponent_team_score += points

    # Update game with calculated scores
    game.playing_team_score = playing_team_score
    game.opponent_team_score = opponent_team_score
    db.commit()

    typer.echo(
        f"Updated game scores: {game.playing_team.name} {playing_team_score} - {opponent_team_score} {game.opponent_team.name}"
    )
