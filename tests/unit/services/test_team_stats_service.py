"""
Tests for the team stats service.
"""

from unittest.mock import Mock, patch

import pytest

from app.services.team_stats_service import TeamStatsService


class TestTeamStatsService:
    """Test cases for TeamStatsService class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db_session):
        """Create a TeamStatsService instance with mocked session."""
        return TeamStatsService(mock_db_session)

    def test_calculate_team_score_basic(self, service):
        """Test basic team score calculation."""
        # Create mock player stats
        player_stats = [
            Mock(total_ftm=1, total_2pm=2, total_3pm=1),  # 1 + 4 + 3 = 8 points
            Mock(total_ftm=2, total_2pm=1, total_3pm=0),  # 2 + 2 + 0 = 4 points
        ]

        result = service._calculate_team_score(player_stats)
        assert result == 12

    def test_calculate_team_score_empty(self, service):
        """Test team score calculation with no players."""
        result = service._calculate_team_score([])
        assert result == 0

    def test_calculate_team_fg_stats_basic(self, service):
        """Test field goal statistics calculation."""
        player_stats = [
            Mock(total_2pm=2, total_2pa=4, total_3pm=1, total_3pa=2),  # 3 made, 6 attempted
            Mock(total_2pm=1, total_2pa=3, total_3pm=0, total_3pa=1),  # 1 made, 4 attempted
        ]

        fgm, fga = service._calculate_team_fg_stats(player_stats)
        assert fgm == 4  # 3 + 1
        assert fga == 10  # 6 + 4

    def test_calculate_team_fg_stats_empty(self, service):
        """Test field goal statistics with no players."""
        fgm, fga = service._calculate_team_fg_stats([])
        assert fgm == 0
        assert fga == 0

    def test_calculate_offensive_rating_perfect(self, service):
        """Test offensive rating calculation with perfect stats."""
        rating = service._calculate_offensive_rating(100, 100)
        assert rating == 100

    def test_calculate_offensive_rating_zero(self, service):
        """Test offensive rating calculation with zero stats."""
        rating = service._calculate_offensive_rating(0, 0)
        assert rating == 0

    def test_calculate_offensive_rating_moderate(self, service):
        """Test offensive rating calculation with moderate stats."""
        rating = service._calculate_offensive_rating(50, 50)
        assert rating == 50  # 25 + 25

    def test_calculate_defensive_rating_perfect(self, service):
        """Test defensive rating calculation with perfect defense."""
        rating = service._calculate_defensive_rating(0, 0)
        assert rating == 100

    def test_calculate_defensive_rating_poor(self, service):
        """Test defensive rating calculation with poor defense."""
        rating = service._calculate_defensive_rating(100, 100)
        assert rating == 0

    def test_calculate_defensive_rating_moderate(self, service):
        """Test defensive rating calculation with moderate defense."""
        rating = service._calculate_defensive_rating(50, 50)
        assert rating == 50.0  # (50 - 25) + (50 - 25) = 25 + 25 = 50

    def test_get_team_rankings_no_teams(self, service, mock_db_session):
        """Test get_team_rankings with no teams."""
        # Mock empty teams and games
        with patch("app.services.team_stats_service.get_all_teams", return_value=[]):
            with patch("app.services.team_stats_service.get_all_games", return_value=[]):
                result = service.get_team_rankings()
                assert result == []
