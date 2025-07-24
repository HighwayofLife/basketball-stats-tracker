# tests/unit/services/test_awards_service.py

from datetime import date
from unittest.mock import Mock, patch

from app.services.awards_service import (
    _calculate_week_winner,
    calculate_player_of_the_week,
    get_current_season,
    get_season_from_date,
)


class TestSeasonHelpers:
    """Test season utility functions."""

    def test_get_season_from_date(self):
        """Test season calculation from date."""
        assert get_season_from_date(date(2024, 1, 15)) == "2024"
        assert get_season_from_date(date(2024, 6, 30)) == "2024"
        assert get_season_from_date(date(2024, 12, 31)) == "2024"
        assert get_season_from_date(date(2025, 1, 1)) == "2025"

    @patch("app.services.awards_service.date")
    def test_get_current_season(self, mock_date):
        """Test current season calculation."""
        mock_date.today.return_value = date(2024, 7, 15)
        assert get_current_season() == "2024"


class TestCalculateWeekWinner:
    """Test week winner calculation logic."""

    def test_calculate_week_winner_single_winner(self):
        """Test single winner calculation."""
        session = Mock()

        # Mock game with player stats
        game = Mock()
        stat1 = Mock()
        stat1.player_id = 1
        stat1.total_2pm = 5  # 10 points
        stat1.total_3pm = 2  # 6 points
        stat1.total_ftm = 3  # 3 points
        # Total: 19 points

        stat2 = Mock()
        stat2.player_id = 2
        stat2.total_2pm = 3  # 6 points
        stat2.total_3pm = 1  # 3 points
        stat2.total_ftm = 2  # 2 points
        # Total: 11 points

        game.player_game_stats = [stat1, stat2]
        weekly_games = [game]

        # Mock player lookup
        mock_player = Mock()
        mock_player.name = "Test Player"
        mock_player.player_of_the_week_awards = 0
        session.query.return_value.filter.return_value.first.return_value = mock_player

        with patch("app.services.awards_service.crud_player.get_player_by_id", return_value=mock_player):
            winner_id = _calculate_week_winner(session, weekly_games, date(2024, 1, 1))

        assert winner_id == 1
        assert mock_player.player_of_the_week_awards == 1

    def test_calculate_week_winner_tie(self):
        """Test tie handling - both players get awards."""
        session = Mock()

        # Mock game with tied players
        game = Mock()
        stat1 = Mock()
        stat1.player_id = 1
        stat1.total_2pm = 5  # 10 points
        stat1.total_3pm = 2  # 6 points
        stat1.total_ftm = 4  # 4 points
        # Total: 20 points

        stat2 = Mock()
        stat2.player_id = 2
        stat2.total_2pm = 6  # 12 points
        stat2.total_3pm = 1  # 3 points
        stat2.total_ftm = 5  # 5 points
        # Total: 20 points (tie!)

        game.player_game_stats = [stat1, stat2]
        weekly_games = [game]

        # Mock player lookups
        mock_player1 = Mock()
        mock_player1.name = "Player 1"
        mock_player1.player_of_the_week_awards = 0

        mock_player2 = Mock()
        mock_player2.name = "Player 2"
        mock_player2.player_of_the_week_awards = 0

        def mock_get_player(session, player_id):
            return mock_player1 if player_id == 1 else mock_player2

        with patch("app.services.awards_service.crud_player.get_player_by_id", side_effect=mock_get_player):
            winner_id = _calculate_week_winner(session, weekly_games, date(2024, 1, 1))

        # Both players should get awards in case of tie
        assert winner_id in [1, 2]  # Returns first player ID for logging
        assert mock_player1.player_of_the_week_awards == 1
        assert mock_player2.player_of_the_week_awards == 1

    def test_calculate_week_winner_no_stats(self):
        """Test week with no player stats."""
        session = Mock()

        game = Mock()
        game.player_game_stats = []
        weekly_games = [game]

        winner_id = _calculate_week_winner(session, weekly_games, date(2024, 1, 1))
        assert winner_id is None

    def test_calculate_week_winner_no_games(self):
        """Test week with no games."""
        session = Mock()
        weekly_games = []

        winner_id = _calculate_week_winner(session, weekly_games, date(2024, 1, 1))
        assert winner_id is None


class TestCalculatePlayerOfTheWeek:
    """Test main POTW calculation function."""

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service._calculate_week_winner")
    def test_calculate_all_seasons(self, mock_week_winner, mock_get_games):
        """Test calculating awards for all seasons."""
        session = Mock()

        # Mock games from different seasons
        game1 = Mock()
        game1.date = date(2024, 1, 15)  # Monday

        game2 = Mock()
        game2.date = date(2024, 1, 22)  # Following Monday (different week)

        game3 = Mock()
        game3.date = date(2025, 2, 10)  # Different season

        mock_get_games.return_value = [game1, game2, game3]
        mock_week_winner.side_effect = [1, 2, 3]  # Winners for each week

        results = calculate_player_of_the_week(session, season=None, recalculate=False)

        # Should process 3 weeks across 2 seasons
        assert mock_week_winner.call_count == 3
        assert results == {"2024": 2, "2025": 1}

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service._calculate_week_winner")
    def test_calculate_specific_season(self, mock_week_winner, mock_get_games):
        """Test calculating awards for specific season."""
        session = Mock()

        # Mock games from different seasons
        game1 = Mock()
        game1.date = date(2024, 1, 15)

        game2 = Mock()
        game2.date = date(2025, 1, 15)  # Different season - should be filtered out

        mock_get_games.return_value = [game1, game2]
        mock_week_winner.return_value = 1

        results = calculate_player_of_the_week(session, season="2024", recalculate=False)

        # Should only process 2024 game
        assert mock_week_winner.call_count == 1
        assert results == {"2024": 1}

    @patch("app.services.awards_service.crud_game.get_all_games")
    def test_calculate_with_recalculate(self, mock_get_games):
        """Test recalculate flag resets awards."""
        session = Mock()
        mock_get_games.return_value = []

        calculate_player_of_the_week(session, season=None, recalculate=True)

        # Should reset all player awards
        session.query.assert_called_once()
        session.query.return_value.update.assert_called_once_with({"player_of_the_week_awards": 0})

    @patch("app.services.awards_service.crud_game.get_all_games")
    def test_calculate_no_games(self, mock_get_games):
        """Test calculation with no games."""
        session = Mock()
        mock_get_games.return_value = []

        results = calculate_player_of_the_week(session, season=None, recalculate=False)

        assert results == {}

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service._calculate_week_winner")
    def test_week_grouping(self, mock_week_winner, mock_get_games):
        """Test that games are properly grouped by week."""
        session = Mock()

        # Games on same week (Monday-Sunday)
        monday = date(2024, 1, 15)  # Monday
        tuesday = date(2024, 1, 16)  # Tuesday (same week)
        sunday = date(2024, 1, 21)  # Sunday (same week)
        next_monday = date(2024, 1, 22)  # Monday (next week)

        game1 = Mock()
        game1.date = monday

        game2 = Mock()
        game2.date = tuesday

        game3 = Mock()
        game3.date = sunday

        game4 = Mock()
        game4.date = next_monday

        mock_get_games.return_value = [game1, game2, game3, game4]
        mock_week_winner.return_value = 1

        calculate_player_of_the_week(session, season=None, recalculate=False)

        # Should be called twice - once for each week
        assert mock_week_winner.call_count == 2

        # Check that first three games are grouped together
        first_call_games = mock_week_winner.call_args_list[0][0][1]
        assert len(first_call_games) == 3

        # Check that last game is in separate week
        second_call_games = mock_week_winner.call_args_list[1][0][1]
        assert len(second_call_games) == 1
