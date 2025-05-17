"""
Service for importing roster and game stats from CSV files.
Handles all parsing, validation, and DB operations for CSV imports.
"""

import csv
from pathlib import Path
from typing import cast

import typer
from sqlalchemy.exc import SQLAlchemyError

import app.data_access.database_manager as db_manager
from app.config import SHOT_MAPPING
from app.data_access.models import Player, Team
from app.schemas.csv_schemas import GameInfoSchema, GameStatsCSVInputSchema, PlayerStatsRowSchema
from app.services.game_service import GameService
from app.services.player_service import PlayerService
from app.services.stats_entry_service import StatsEntryService
from app.utils.input_parser import parse_quarter_shot_string


def import_roster_from_csv(roster_file: str, dry_run: bool = False) -> bool:
    """
    Import teams and players from a CSV file. Returns True on success, False on error.
    """
    roster_path = Path(roster_file)
    if not roster_path.exists():
        typer.echo(f"Error: File '{roster_file}' not found.")
        return False

    try:
        with open(roster_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            required_fields = ["team_name", "player_name", "jersey_number"]
            missing_fields = [field for field in required_fields if field not in (reader.fieldnames or [])]
            if missing_fields:
                typer.echo(f"Error: CSV file missing required headers: {', '.join(missing_fields)}")
                return False
            team_data = {}
            player_data = []
            for row in reader:
                team_name = row["team_name"].strip()
                player_name = row["player_name"].strip()
                try:
                    jersey_number = int(row["jersey_number"])
                except (ValueError, TypeError):
                    typer.echo(
                        f"Warning: Invalid jersey number '{row['jersey_number']}' for player '{player_name}'. Skipping."
                    )
                    continue
                if team_name not in team_data:
                    team_data[team_name] = {"count": 0}
                team_data[team_name]["count"] += 1
                player_data.append({"team_name": team_name, "name": player_name, "jersey_number": jersey_number})
        typer.echo(f"\nRoster import summary from {roster_file}:")
        typer.echo(f"Found {len(team_data)} teams and {len(player_data)} players.\n")
        for team_name, info in team_data.items():
            typer.echo(f"Team: {team_name} - {info['count']} players")
        if dry_run:
            typer.echo("\nDry run mode: No changes were made to the database.")
            return True
        with db_manager.db_manager.get_db_session() as db:
            teams_added = 0
            teams_existing = 0
            players_added = 0
            players_existing = 0
            players_error = 0
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
                    if (
                        existing_player.name == player["name"]
                        and existing_player.jersey_number == player["jersey_number"]
                    ):
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
            db.commit()
            typer.echo("\nRoster import completed:")
            typer.echo(f"Teams: {teams_added} added, {teams_existing} already existed")
            typer.echo(
                f"Players: {players_added} added, {players_existing} already existed, {players_error} errors/conflicts"
            )
            return True
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
    except Exception as e: # pylint: disable=broad-except
        typer.echo(f"Unexpected error importing roster: {e}")
        return False


def import_game_stats_from_csv(game_stats_file: str, dry_run: bool = False) -> bool:
    """
    Import game statistics from a CSV file. Returns True on success, False on error.
    """
    game_stats_path = Path(game_stats_file)
    if not game_stats_path.exists():
        typer.echo(f"Error: File '{game_stats_file}' not found.")
        return False
    try:
        with open(game_stats_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            if not rows:
                typer.echo("Error: CSV file is empty.")
                return False
            game_info_data = {}
            player_stats_header = None
            player_stats_rows = []
            section = "unknown"
            for row in rows:
                if not row:
                    continue
                if row[0] == "GAME_INFO_KEY":
                    section = "game_info"
                    continue
                elif row[0] == "PLAYER_STATS_HEADER":
                    section = "player_stats_header"
                    player_stats_header = row[1:]
                    continue
                elif row[0] == "PLAYER_DATA":
                    section = "player_stats"
                if section == "game_info" and len(row) >= 2:
                    game_info_data[row[0]] = row[1]
                elif section == "player_stats" and len(row) >= 2:
                    player_stats_rows.append(row[1:])
            if not game_info_data or not player_stats_header or not player_stats_rows:
                typer.echo("Error: CSV file doesn't have the required structure.")
                return False
            try:
                game_info_valid = {
                    "PlayingTeam": game_info_data.get("Playing Team", ""),
                    "OpponentTeam": game_info_data.get("Opponent Team", ""),
                    "Date": game_info_data.get("Date", ""),
                }
                game_info = GameInfoSchema(**game_info_valid)
            except ValueError as e:
                typer.echo(f"Error validating game information: {e}")
                return False
            player_stats = []
            for i, player_row in enumerate(player_stats_rows):
                if len(player_row) < len(player_stats_header):
                    player_row.extend([""] * (len(player_stats_header) - len(player_row)))
                elif len(player_row) > len(player_stats_header):
                    player_row = player_row[: len(player_stats_header)]
                player_dict = {
                    "TeamName": "",
                    "PlayerJersey": 0,
                    "PlayerName": "",
                    "Fouls": 0,
                    "QT1Shots": "",
                    "QT2Shots": "",
                    "QT3Shots": "",
                    "QT4Shots": "",
                }
                for j, header in enumerate(player_stats_header):
                    header_normalized = header.replace(" ", "")
                    if header_normalized == "TeamName" or header_normalized == "Team":
                        player_dict["TeamName"] = player_row[j]
                    elif header_normalized == "PlayerJersey" or header_normalized == "Jersey":
                        try:
                            player_dict["PlayerJersey"] = int(player_row[j])
                        except (ValueError, TypeError):
                            typer.echo(f"Warning: Invalid jersey number '{player_row[j]}' in row {i + 1}. Using 0.")
                            player_dict["PlayerJersey"] = 0
                    elif header_normalized == "PlayerName" or header_normalized == "Name":
                        player_dict["PlayerName"] = player_row[j]
                    elif header_normalized == "Fouls":
                        try:
                            player_dict["Fouls"] = int(player_row[j]) if player_row[j] else 0
                        except (ValueError, TypeError):
                            typer.echo(f"Warning: Invalid fouls '{player_row[j]}' in row {i + 1}. Using 0.")
                            player_dict["Fouls"] = 0
                    elif header_normalized == "QT1Shots":
                        player_dict["QT1Shots"] = player_row[j]
                    elif header_normalized == "QT2Shots":
                        player_dict["QT2Shots"] = player_row[j]
                    elif header_normalized == "QT3Shots":
                        player_dict["QT3Shots"] = player_row[j]
                    elif header_normalized == "QT4Shots":
                        player_dict["QT4Shots"] = player_row[j]
                player_stats.append(
                    PlayerStatsRowSchema(
                        TeamName=str(player_dict["TeamName"]),
                        PlayerJersey=cast(int, player_dict["PlayerJersey"]),
                        PlayerName=str(player_dict["PlayerName"]),
                        Fouls=cast(int, player_dict["Fouls"]),
                        QT1Shots=str(player_dict["QT1Shots"]),
                        QT2Shots=str(player_dict["QT2Shots"]),
                        QT3Shots=str(player_dict["QT3Shots"]),
                        QT4Shots=str(player_dict["QT4Shots"]),
                    )
                )
            validated_data = GameStatsCSVInputSchema(
                game_info=game_info,
                player_stats=player_stats,
            )
            typer.echo(f"\nGame stats import summary from {game_stats_file}:")
            typer.echo(
                f"Game: {validated_data.game_info.PlayingTeam} vs {validated_data.game_info.OpponentTeam} "
                f"on {validated_data.game_info.Date}"
            )
            typer.echo(f"Players: {len(validated_data.player_stats)}")
            if dry_run:
                typer.echo("\nDry run mode: No changes were made to the database.")
                return True
            with db_manager.db_manager.get_db_session() as db:
                game_service = GameService(db)
                player_service = PlayerService(db)
                stats_entry_service = StatsEntryService(db, parse_quarter_shot_string, SHOT_MAPPING)
                game = game_service.add_game(
                    validated_data.game_info.Date,
                    validated_data.game_info.PlayingTeam,
                    validated_data.game_info.OpponentTeam,
                )
                typer.echo(
                    f"\nCreated game #{game.id}: {game.playing_team.name} vs {game.opponent_team.name} on {game.date}"
                )
                players_processed = 0
                players_error = 0
                for player_stat in validated_data.player_stats:
                    try:
                        team = game_service.get_or_create_team(player_stat.TeamName)
                        player = player_service.get_or_create_player(
                            team.id, player_stat.PlayerJersey, player_stat.PlayerName
                        )
                        stats_entry_service.record_player_game_performance(
                            game.id,
                            player.id,
                            player_stat.Fouls,
                            [player_stat.QT1Shots, player_stat.QT2Shots, player_stat.QT3Shots, player_stat.QT4Shots],
                        )
                        players_processed += 1
                    except (ValueError, KeyError, TypeError) as e:
                        typer.echo(f"Data error processing player {player_stat.PlayerName}: {e}")
                    except OSError as e:
                        typer.echo(f"I/O error processing player {player_stat.PlayerName}: {e}")
                        players_error += 1
                    except SQLAlchemyError as e:
                        typer.echo(f"Database error processing player {player_stat.PlayerName}: {e}")
                        players_error += 1
                        players_error += 1
                typer.echo(
                    f"Game stats import completed: {players_processed} players processed, {players_error} errors"
                )
                return True
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
