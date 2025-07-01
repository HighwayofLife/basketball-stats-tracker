"""Service for calculating game scores from player statistics."""

from sqlalchemy.orm import Session

from app.data_access.models import Game, PlayerGameStats
from app.utils.stats_calculator import calculate_points


class ScoreCalculationService:
    """Service for calculating game scores from player statistics.

    This service centralizes the logic for calculating team scores based on
    individual player statistics, eliminating duplicate code across the application.
    """

    @staticmethod
    def calculate_player_points(stat: PlayerGameStats) -> int:
        """Calculate total points for a player's game statistics.

        Args:
            stat: Player game statistics

        Returns:
            Total points scored by the player
        """
        return calculate_points(stat.total_ftm, stat.total_2pm, stat.total_3pm)

    @staticmethod
    def calculate_game_scores(game: Game, player_stats: list[PlayerGameStats]) -> tuple[int, int]:
        """Calculate team scores for a game from player statistics.

        Args:
            game: The game to calculate scores for
            player_stats: List of player game statistics for this game

        Returns:
            Tuple of (playing_team_score, opponent_team_score)
        """
        playing_team_score = 0
        opponent_team_score = 0

        for stat in player_stats:
            # Calculate player's total points
            points = ScoreCalculationService.calculate_player_points(stat)

            # Add to appropriate team total
            if stat.player.team_id == game.playing_team_id:
                playing_team_score += points
            elif stat.player.team_id == game.opponent_team_id:
                opponent_team_score += points

        return playing_team_score, opponent_team_score

    @staticmethod
    def calculate_game_scores_from_db(db: Session, game_id: int) -> tuple[int, int]:
        """Calculate team scores for a game by fetching player stats from database.

        Args:
            db: Database session
            game_id: ID of the game to calculate scores for

        Returns:
            Tuple of (playing_team_score, opponent_team_score)
        """
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game with id {game_id} not found")

        player_stats = db.query(PlayerGameStats).filter(PlayerGameStats.game_id == game_id).all()

        return ScoreCalculationService.calculate_game_scores(game, player_stats)

    @staticmethod
    def update_game_scores(db: Session, game: Game, commit: bool = True) -> None:
        """Update game scores in the database based on player statistics.

        Args:
            db: Database session
            game: The game to update scores for
            commit: Whether to commit the transaction (default True for backward compatibility)
        """
        player_stats = db.query(PlayerGameStats).filter(PlayerGameStats.game_id == game.id).all()

        playing_team_score, opponent_team_score = ScoreCalculationService.calculate_game_scores(game, player_stats)

        # Update game with calculated scores
        game.playing_team_score = playing_team_score
        game.opponent_team_score = opponent_team_score

        if commit:
            db.commit()
