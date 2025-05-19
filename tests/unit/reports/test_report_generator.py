"""
Test module for the ReportGenerator.
"""

from unittest.mock import MagicMock

import pytest

from app.data_access.models import Game, Player, PlayerGameStats, Team
from app.reports.report_generator import ReportGenerator


class TestReportGenerator:
    """Tests for the ReportGenerator."""

    @pytest.fixture
    def mock_game_data(self):
        """Create mock game data for testing reports."""
        team_a = Team(id=1, name="Team A")
        team_b = Team(id=2, name="Team B")

        game = Game(
            id=1, date="2025-05-01", playing_team_id=1, opponent_team_id=2, playing_team=team_a, opponent_team=team_b
        )

        player_a1 = Player(id=1, name="Player One", jersey_number=10, team_id=1, team=team_a)
        player_a2 = Player(id=2, name="Player Two", jersey_number=23, team_id=1, team=team_a)
        player_b1 = Player(id=3, name="Player Alpha", jersey_number=5, team_id=2, team=team_b)
        player_b2 = Player(id=4, name="Player Beta", jersey_number=15, team_id=2, team=team_b)

        player_game_stats = [
            # Team A players
            PlayerGameStats(
                id=1,
                game_id=1,
                player_id=1,
                fouls=2,
                total_ftm=3,
                total_fta=4,
                total_2pm=5,
                total_2pa=8,
                total_3pm=2,
                total_3pa=5,
                player=player_a1,
                game=game,
            ),
            PlayerGameStats(
                id=2,
                game_id=1,
                player_id=2,
                fouls=3,
                total_ftm=1,
                total_fta=2,
                total_2pm=4,
                total_2pa=6,
                total_3pm=1,
                total_3pa=3,
                player=player_a2,
                game=game,
            ),
            # Team B players
            PlayerGameStats(
                id=3,
                game_id=1,
                player_id=3,
                fouls=1,
                total_ftm=0,
                total_fta=2,
                total_2pm=6,
                total_2pa=10,
                total_3pm=3,
                total_3pa=7,
                player=player_b1,
                game=game,
            ),
            PlayerGameStats(
                id=4,
                game_id=1,
                player_id=4,
                fouls=4,
                total_ftm=4,
                total_fta=4,
                total_2pm=3,
                total_2pa=5,
                total_3pm=0,
                total_3pa=2,
                player=player_b2,
                game=game,
            ),
        ]

        return {"game": game, "player_game_stats": player_game_stats, "teams": [team_a, team_b]}

    @pytest.fixture
    def mock_db_session(self, mock_game_data):
        """Create a mock database session."""
        mock_session = MagicMock()

        # Mock query.filter methods to return appropriate data
        def mock_get_game(game_id):
            if game_id == 1:
                return mock_game_data["game"]
            return None

        def mock_get_player_game_stats(game_id):
            if game_id == 1:
                return mock_game_data["player_game_stats"]
            return []

        mock_session.query.return_value.filter.return_value.first.side_effect = mock_get_game
        mock_session.query.return_value.filter.return_value.all.side_effect = mock_get_player_game_stats

        return mock_session

    @pytest.fixture
    def mock_stats_calculator(self):
        """Create a mock stats calculator module."""
        mock_module = MagicMock()

        # Mock the calculation functions
        mock_module.calculate_percentage.side_effect = lambda makes, attempts: makes / attempts if attempts else None

        mock_module.calculate_points.side_effect = lambda ftm, fg2m, fg3m: ftm + 2 * fg2m + 3 * fg3m

        mock_module.calculate_efg.side_effect = (
            lambda total_fgm, fg3m, total_fga: (total_fgm + 0.5 * fg3m) / total_fga if total_fga else None
        )

        mock_module.calculate_ts.side_effect = (
            lambda points, total_fga, fta: points / (2 * (total_fga + 0.44 * fta)) if (total_fga + fta) else None
        )

        return mock_module

    def test_init(self, db_session, mock_stats_calculator):
        """Test initializing the report generator."""
        report_generator = ReportGenerator(db_session, mock_stats_calculator)
        assert report_generator.db_session == db_session
        assert report_generator.stats_calculator == mock_stats_calculator

    def test_get_game_box_score_data(self, mock_db_session, mock_stats_calculator, mock_game_data):
        """Test getting game box score data."""
        report_generator = ReportGenerator(mock_db_session, mock_stats_calculator)

        player_stats, game_info = report_generator.get_game_box_score_data(1)

        # Check game info
        assert game_info["date"] == "2025-05-01"
        assert game_info["playing_team"] == "Team A"
        assert game_info["opponent_team"] == "Team B"

        # Check player stats
        assert len(player_stats) == 4

        # Check the first player's stats
        first_player = player_stats[0]
        assert first_player["name"] == "Player One"
        assert first_player["team"] == "Team A"
        assert first_player["jersey"] == 10
        assert first_player["fouls"] == 2
        assert first_player["ftm"] == 3
        assert first_player["fta"] == 4
        assert first_player["ft_pct"] == 0.75
        assert first_player["fg2m"] == 5
        assert first_player["fg2a"] == 8
        assert first_player["fg2_pct"] == 0.625
        assert first_player["fg3m"] == 2
        assert first_player["fg3a"] == 5
        assert first_player["fg3_pct"] == 0.4
        assert first_player["points"] == 19  # 3 FT + 5*2 2P + 2*3 3P = 3 + 10 + 6 = 19
        assert first_player["efg"] == 0.5384615384615384  # (7 + 0.5*2) / 13 = 8/13 = 0.615...

        # Check mock calls
        mock_db_session.query.assert_called()
        mock_stats_calculator.calculate_points.assert_called()
        mock_stats_calculator.calculate_percentage.assert_called()
        mock_stats_calculator.calculate_efg.assert_called()
        mock_stats_calculator.calculate_ts.assert_called()

    def test_get_game_box_score_data_not_found(self, mock_db_session, mock_stats_calculator):
        """Test getting game box score data for a non-existent game."""
        report_generator = ReportGenerator(mock_db_session, mock_stats_calculator)

        # Try to get data for game with ID 999 (non-existent)
        with pytest.raises(ValueError) as excinfo:
            report_generator.get_game_box_score_data(999)

        assert "Game not found" in str(excinfo.value)
