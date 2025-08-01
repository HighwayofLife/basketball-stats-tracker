# tests/unit/services/test_individual_season_awards.py

"""
Individual unit tests for each season award calculation function.
"""

from datetime import date
from unittest.mock import Mock, patch

from app.services.awards_service import (
    calculate_air_assault,
    calculate_air_ball_artist,
    calculate_charity_stripe_regular,
    calculate_curry_wannabe_award,
    calculate_defensive_tackle,
    calculate_efficiency_expert,
    calculate_hack_a_shaq_award,
    calculate_human_highlight_reel,
    calculate_sharpshooter,
    calculate_top_scorer,
)


class TestIndividualSeasonAwards:
    """Test each season award calculation function individually."""

    def setup_method(self):
        """Set up common mock data for tests."""
        self.mock_session = Mock()
        self.season = "2024"

        # Create mock PlayerGameStats with all required attributes
        self.mock_stat1 = Mock()
        self.mock_stat1.player_id = 1
        self.mock_stat1.total_2pm = 10
        self.mock_stat1.total_2pa = 20
        self.mock_stat1.total_3pm = 5
        self.mock_stat1.total_3pa = 10
        self.mock_stat1.total_ftm = 8
        self.mock_stat1.total_fta = 10
        self.mock_stat1.fouls = 2

        self.mock_stat2 = Mock()
        self.mock_stat2.player_id = 2
        self.mock_stat2.total_2pm = 8
        self.mock_stat2.total_2pa = 16
        self.mock_stat2.total_3pm = 3
        self.mock_stat2.total_3pa = 8
        self.mock_stat2.total_ftm = 6
        self.mock_stat2.total_fta = 8
        self.mock_stat2.fouls = 4

        # Add additional mock stats to meet minimum foul requirement for defensive tackle
        self.mock_stat3 = Mock()
        self.mock_stat3.player_id = 1
        self.mock_stat3.total_2pm = 5
        self.mock_stat3.total_2pa = 10
        self.mock_stat3.total_3pm = 2
        self.mock_stat3.total_3pa = 5
        self.mock_stat3.total_ftm = 3
        self.mock_stat3.total_fta = 4
        self.mock_stat3.fouls = 3

        self.mock_stat4 = Mock()
        self.mock_stat4.player_id = 2
        self.mock_stat4.total_2pm = 4
        self.mock_stat4.total_2pa = 8
        self.mock_stat4.total_3pm = 1
        self.mock_stat4.total_3pa = 3
        self.mock_stat4.total_ftm = 2
        self.mock_stat4.total_fta = 3
        self.mock_stat4.fouls = 7

        # Create mock games
        self.mock_game1 = Mock()
        self.mock_game1.date = date(2024, 1, 15)
        self.mock_game1.player_game_stats = [self.mock_stat1]

        self.mock_game2 = Mock()
        self.mock_game2.date = date(2024, 2, 15)
        self.mock_game2.player_game_stats = [self.mock_stat2]

        self.mock_game3 = Mock()
        self.mock_game3.date = date(2024, 3, 15)
        self.mock_game3.player_game_stats = [self.mock_stat3]

        self.mock_game4 = Mock()
        self.mock_game4.date = date(2024, 4, 15)
        self.mock_game4.player_game_stats = [self.mock_stat4]

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_top_scorer(self, mock_create_award, mock_get_season, mock_get_games):
        """Test top scorer award calculation."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_top_scorer(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1 should win with 33 points (10*2 + 5*3 + 8) vs Player 2's 29 points (8*2 + 3*3 + 6)
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "top_scorer"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_sharpshooter(self, mock_create_award, mock_get_season, mock_get_games):
        """Test sharpshooter award calculation (best 3pt%)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_sharpshooter(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1 should win with 50% (5/10) vs Player 2's 37.5% (3/8)
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "sharpshooter"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_efficiency_expert(self, mock_create_award, mock_get_season, mock_get_games):
        """Test efficiency expert award calculation (best FG%)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_efficiency_expert(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1: 15 made / 30 attempts = 50%
        # Player 2: 11 made / 24 attempts = 45.8%
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "efficiency_expert"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_charity_stripe_regular(self, mock_create_award, mock_get_season, mock_get_games):
        """Test charity stripe regular award calculation (most FT made)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_charity_stripe_regular(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1 should win with 8 FTM vs Player 2's 6 FTM
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "charity_stripe_regular"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_human_highlight_reel(self, mock_create_award, mock_get_season, mock_get_games):
        """Test human highlight reel award calculation (most FG made)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_human_highlight_reel(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1 should win with 15 FG made (10+5) vs Player 2's 11 FG made (8+3)
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "human_highlight_reel"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_defensive_tackle(self, mock_create_award, mock_get_season, mock_get_games):
        """Test defensive tackle award calculation (highest fouls-per-game average with min 10 fouls)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2, self.mock_game3, self.mock_game4]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_defensive_tackle(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 2 should win: 11 total fouls (4+7) in 2 games = 5.5 fouls/game
        # vs Player 1: 5 total fouls (2+3) in 2 games = 2.5 fouls/game (doesn't qualify - <10 total)
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 2
        assert call_args["award_type"] == "defensive_tackle"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_air_ball_artist(self, mock_create_award, mock_get_season, mock_get_games):
        """Test air ball artist award calculation (most 3pt misses)."""
        # Fix test data to have different 3pt miss counts
        self.mock_stat1.total_3pa = 12  # Will have 7 misses (12-5)
        self.mock_stat2.total_3pa = 8  # Will have 5 misses (8-3)

        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_air_ball_artist(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1 should win with 7 3pt misses vs Player 2's 5 3pt misses
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "air_ball_artist"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_air_assault(self, mock_create_award, mock_get_season, mock_get_games):
        """Test air assault award calculation (most shot attempts)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_air_assault(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1 should win with 40 total attempts (20+10+10) vs Player 2's 32 attempts (16+8+8)
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "air_assault"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_curry_wannabe_award(self, mock_create_award, mock_get_season, mock_get_games):
        """Test Curry Wannabe award calculation (most 3PM)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2, self.mock_game3, self.mock_game4]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_curry_wannabe_award(self.mock_session, self.season, recalculate=False)

        assert result == 1  # One award given
        mock_create_award.assert_called_once()
        # Player 1 should win with 7 total 3PM (5+2) vs Player 2's 4 total 3PM (3+1)
        call_args = mock_create_award.call_args[1]
        assert call_args["player_id"] == 1
        assert call_args["award_type"] == "curry_wannabe"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_calculate_hack_a_shaq_award(self, mock_create_award, mock_get_season, mock_get_games):
        """Test Hack-a-Shaq award calculation (most FT misses)."""
        mock_get_games.return_value = [self.mock_game1, self.mock_game2, self.mock_game3, self.mock_game4]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_hack_a_shaq_award(self.mock_session, self.season, recalculate=False)

        assert result == 2  # Two awards given (tie)
        assert mock_create_award.call_count == 2
        # Player 1: 3 FT misses (2+1), Player 2: 3 FT misses (2+1) - they tie
        call_args = mock_create_award.call_args[1]
        assert call_args["award_type"] == "hack_a_shaq"

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    def test_no_awards_when_no_data(self, mock_get_season, mock_get_games):
        """Test that no awards are given when there's no game data."""
        mock_get_games.return_value = []
        mock_get_season.return_value = self.season

        result = calculate_top_scorer(self.mock_session, self.season, recalculate=False)
        assert result == 0  # No awards given

    @patch("app.services.awards_service.crud_game.get_all_games")
    @patch("app.services.awards_service.get_season_from_date")
    @patch("app.services.awards_service.create_player_award_safe")
    def test_award_handles_ties(self, mock_create_award, mock_get_season, mock_get_games):
        """Test that awards handle ties correctly by giving awards to all tied players."""
        # Create identical stats for tie scenario
        self.mock_stat2.total_2pm = 10  # Same as player 1
        self.mock_stat2.total_3pm = 5  # Same as player 1
        self.mock_stat2.total_ftm = 8  # Same as player 1

        mock_get_games.return_value = [self.mock_game1, self.mock_game2]
        mock_get_season.side_effect = lambda d: self.season
        mock_create_award.return_value = Mock()

        result = calculate_top_scorer(self.mock_session, self.season, recalculate=False)

        assert result == 2  # Both players tied, both get awards
        assert mock_create_award.call_count == 2
