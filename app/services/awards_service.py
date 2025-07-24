# app/services/awards_service.py

from sqlalchemy.orm import Session
from app.data_access.crud import crud_player, crud_game
from app.data_access.models import Game, Player
from collections import defaultdict
from datetime import timedelta

def get_player_with_highest_score(session: Session, players_of_the_week: list[int]):
    """Gets the player with the highest score in a given week."""
    # This is a placeholder implementation. The actual logic will be more complex.
    return 1  # Returning a placeholder player ID

def calculate_player_of_the_week(session: Session):
    """Calculates the player of the week for each week of the season."""
    games = crud_game.get_all_games(session)
    games_by_week = defaultdict(list)

    for game in games:
        week_start = game.date - timedelta(days=game.date.weekday())
        games_by_week[week_start].append(game)

    for week_start, weekly_games in games_by_week.items():
        player_scores = defaultdict(int)
        for game in weekly_games:
            for stat in game.player_game_stats:
                player_scores[stat.player_id] += (stat.total_2pm * 2) + (stat.total_3pm * 3) + stat.total_ftm

        if player_scores:
            top_player_id = max(player_scores, key=player_scores.get)
            player = crud_player.get_player_by_id(session, top_player_id)
            if player:
                player.player_of_the_week_awards += 1

    session.commit()
