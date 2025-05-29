#!/usr/bin/env python3
"""
Seed script for the Basketball Stats Tracker application.
Provides basic data for development and testing purposes.
"""

from sqlalchemy.orm import Session

from app.data_access.database_manager import db_manager
from app.data_access.models import Game, Player, Team


def seed_teams(db: Session):
    """Seed basic team data."""
    teams_to_define = [
        Team(name="Lions"),
        Team(name="Tigers"),
        Team(name="Bears"),
        Team(name="Eagles"),
        Team(name="Sharks"),
        Team(name="Guest Players", display_name="Guest Players"),  # For substitute players
    ]

    added_to_session = False
    # Add teams if they don't exist
    for team_def in teams_to_define:
        existing = db.query(Team).filter(Team.name == team_def.name).first()
        if not existing:
            db.add(team_def)
            added_to_session = True

    if added_to_session:
        db.commit()
        print("Committed new teams to the database.")
    else:
        print("No new teams to commit (they might already exist).")

    return db.query(Team).all()


def seed_players(db: Session):
    """Seed basic player data."""
    # Get all teams
    teams_in_db = db.query(Team).all()

    # Exit if no teams exist
    if not teams_in_db:
        print("No teams found. Please run seed_teams() first.")
        return []

    added_to_session = False
    # Create 5 players for each team
    for team in teams_in_db:
        for i in range(1, 6):
            jersey_number = i * 10  # 10, 20, 30, 40, 50
            name = f"Player {jersey_number} ({team.name})"

            existing = db.query(Player).filter(Player.team_id == team.id, Player.jersey_number == jersey_number).first()

            if not existing:
                player = Player(team_id=team.id, name=name, jersey_number=jersey_number)
                db.add(player)
                added_to_session = True

    if added_to_session:
        db.commit()
        print("Committed new players to the database.")
    else:
        print("No new players to commit (they might already exist).")

    return db.query(Player).all()


def seed_games(db: Session):
    """Seed basic game data."""
    # Get all teams
    teams_in_db = db.query(Team).all()
    num_teams = len(teams_in_db)

    # Initial check
    if num_teams < 2:
        print("Not enough teams found (need at least 2) to seed games. Please ensure teams exist.")
        return []

    # Define potential games with updated dates
    # Dates are set in late 2024
    potential_games_data: list[dict[str, int | str]] = [
        {"date": "2024-10-05", "playing_team_idx": 0, "opponent_team_idx": 1, "min_teams_required": 2},
        {"date": "2024-10-12", "playing_team_idx": 2, "opponent_team_idx": 3, "min_teams_required": 4},
        {"date": "2024-10-19", "playing_team_idx": 1, "opponent_team_idx": 4, "min_teams_required": 5},
    ]

    games_to_add_to_db = []
    for g_data in potential_games_data:
        min_teams_required = int(g_data["min_teams_required"])  # Explicitly convert to int
        if num_teams >= min_teams_required:
            # Ensure team indices are valid (already implicitly checked by num_teams vs min_teams_required)
            # and that playing_team_id is different from opponent_team_id (guaranteed by index choices)
            games_to_add_to_db.append(
                Game(
                    date=g_data["date"],
                    playing_team_id=teams_in_db[int(g_data["playing_team_idx"])].id,
                    opponent_team_id=teams_in_db[int(g_data["opponent_team_idx"])].id,
                )
            )
        else:
            print(
                f"Skipping game scheduled for {g_data['date']} due to insufficient teams "
                f"(need {g_data['min_teams_required']}, have {num_teams})."
            )

    if not games_to_add_to_db:
        print("No games could be defined for seeding based on the number of available teams.")
        return db.query(Game).all()  # Return existing games if any, or empty list

    # Add games if they don't exist
    actually_added_to_session = False
    for game_obj in games_to_add_to_db:
        existing = (
            db.query(Game)
            .filter(
                Game.date == game_obj.date,
                Game.playing_team_id == game_obj.playing_team_id,
                Game.opponent_team_id == game_obj.opponent_team_id,
            )
            .first()
        )

        if not existing:
            db.add(game_obj)
            actually_added_to_session = True

    if actually_added_to_session:
        db.commit()
        print("Committed new games to the database.")
    else:
        print("No new games to commit (they might already exist or no games were defined for addition).")

    return db.query(Game).all()


def seed_all():
    """Seed all basic data for development."""
    print("Seeding development database...")
    # engine = db_manager.get_engine() # Unused variable

    with db_manager.get_db_session() as db:
        print("Seeding teams...")
        teams = seed_teams(db)
        print(f"Finished seeding teams. Total teams in DB: {len(teams)}.")

        print("Seeding players...")
        players = seed_players(db)
        print(f"Finished seeding players. Total players in DB: {len(players)}.")

        print("Seeding games...")
        games = seed_games(db)
        print(f"Finished seeding games. Total games in DB: {len(games)}.")

    print("Database seeding complete!")


if __name__ == "__main__":
    seed_all()
