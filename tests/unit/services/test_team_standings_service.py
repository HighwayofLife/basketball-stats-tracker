"""Test cases for team standings functionality in SeasonStatsService."""

from unittest.mock import MagicMock

import pytest

from app.services.season_stats_service import SeasonStatsService


class TestTeamStandingsService:
    """Test team standings functionality in SeasonStatsService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def stats_service(self, mock_session):
        """Create a SeasonStatsService instance with mocked session."""
        return SeasonStatsService(mock_session)

    def test_get_team_record_with_existing_stats(self, stats_service, mock_session):
        """Test getting team record when stats already exist."""
        # Mock active season
        mock_season = MagicMock()
        mock_season.code = "2023-24"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_season

        # Mock existing team stats
        mock_stats = MagicMock()
        mock_stats.wins = 10
        mock_stats.losses = 5
        mock_session.query.return_value.filter.return_value.first.return_value = mock_stats

        wins, losses = stats_service.get_team_record(1, "2023-24")

        assert wins == 10
        assert losses == 5

    def test_get_team_record_without_existing_stats(self, stats_service, mock_session):
        """Test getting team record when stats don't exist - should trigger calculation."""
        # Mock active season
        mock_season = MagicMock()
        mock_season.code = "2023-24"

        # Mock stats after calculation
        mock_stats = MagicMock()
        mock_stats.wins = 8
        mock_stats.losses = 3

        # Set up the filter chain - first call returns None (no existing stats), second returns stats
        mock_session.query.return_value.filter.return_value.first.side_effect = [None, mock_stats]

        # Mock update_team_season_stats method
        stats_service.update_team_season_stats = MagicMock()

        wins, losses = stats_service.get_team_record(1, "2023-24")

        assert wins == 8
        assert losses == 3
        stats_service.update_team_season_stats.assert_called_once_with(1, "2023-24")

    def test_get_team_record_no_active_season(self, stats_service, mock_session):
        """Test getting team record when no active season exists."""
        # Mock no active season, no latest game
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value.order_by.return_value.first.return_value = None

        wins, losses = stats_service.get_team_record(1)

        assert wins == 0
        assert losses == 0

    def test_get_teams_records_multiple_teams(self, stats_service, mock_session):
        """Test getting records for multiple teams efficiently."""
        # Mock existing stats for some teams
        mock_stats_1 = MagicMock()
        mock_stats_1.team_id = 1
        mock_stats_1.wins = 10
        mock_stats_1.losses = 5

        mock_stats_2 = MagicMock()
        mock_stats_2.team_id = 2
        mock_stats_2.wins = 7
        mock_stats_2.losses = 8

        mock_session.query.return_value.filter.return_value.all.return_value = [mock_stats_1, mock_stats_2]

        # Mock update_team_season_stats for missing team
        stats_service.update_team_season_stats = MagicMock()

        # Mock stats after calculation for team 3
        mock_stats_3 = MagicMock()
        mock_stats_3.wins = 4
        mock_stats_3.losses = 11
        mock_session.query.return_value.filter.return_value.first.return_value = mock_stats_3

        records = stats_service.get_teams_records([1, 2, 3], "2023-24")

        assert records[1] == (10, 5)
        assert records[2] == (7, 8)
        assert records[3] == (4, 11)
        stats_service.update_team_season_stats.assert_called_once_with(3, "2023-24")

    def test_get_teams_records_empty_list(self, stats_service, mock_session):
        """Test getting records for empty team list."""
        records = stats_service.get_teams_records([])
        assert records == {}

    def test_get_teams_records_no_season(self, stats_service, mock_session):
        """Test getting records when no season exists."""
        # Mock no active season, no latest game
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value.order_by.return_value.first.return_value = None

        records = stats_service.get_teams_records([1, 2, 3])

        assert records == {1: (0, 0), 2: (0, 0), 3: (0, 0)}

    def test_get_team_standings_sorts_by_win_percentage(self, stats_service, mock_session):
        """Test that team standings are sorted by win percentage."""
        # Mock latest game for season detection
        mock_game = MagicMock()
        mock_game.date = "2023-12-01"
        mock_session.query.return_value.order_by.return_value.first.return_value = mock_game

        # Mock get_season_from_date
        stats_service.get_season_from_date = MagicMock(return_value="2023-24")

        # Mock team season stats
        mock_stats_1 = MagicMock()
        mock_stats_1.team_id = 1
        mock_stats_1.wins = 10
        mock_stats_1.losses = 5
        mock_stats_1.games_played = 15
        mock_stats_1.total_points_for = 1500
        mock_stats_1.total_points_against = 1400
        mock_stats_1.team.name = "Team A"

        mock_stats_2 = MagicMock()
        mock_stats_2.team_id = 2
        mock_stats_2.wins = 8
        mock_stats_2.losses = 7
        mock_stats_2.games_played = 15
        mock_stats_2.total_points_for = 1450
        mock_stats_2.total_points_against = 1450
        mock_stats_2.team.name = "Team B"

        mock_session.query.return_value.join.return_value.filter.return_value.options.return_value.all.return_value = [
            mock_stats_1,
            mock_stats_2,
        ]

        standings = stats_service.get_team_standings()

        assert len(standings) == 2
        # Team A should be first (higher win percentage: 66.7% vs 53.3%)
        assert standings[0]["team_name"] == "Team A"
        assert standings[0]["rank"] == 1
        assert standings[0]["wins"] == 10
        assert standings[0]["losses"] == 5
        assert standings[0]["win_pct"] == pytest.approx(0.667, abs=0.001)

        assert standings[1]["team_name"] == "Team B"
        assert standings[1]["rank"] == 2
        assert standings[1]["wins"] == 8
        assert standings[1]["losses"] == 7
        assert standings[1]["win_pct"] == pytest.approx(0.533, abs=0.001)

    def test_get_team_standings_calculates_games_back(self, stats_service, mock_session):
        """Test that games back is calculated correctly."""
        # Mock latest game for season detection
        mock_game = MagicMock()
        mock_game.date = "2023-12-01"
        mock_session.query.return_value.order_by.return_value.first.return_value = mock_game

        # Mock get_season_from_date
        stats_service.get_season_from_date = MagicMock(return_value="2023-24")

        # Mock team season stats - leader: 12-3, second: 10-5
        mock_stats_1 = MagicMock()
        mock_stats_1.team_id = 1
        mock_stats_1.wins = 12
        mock_stats_1.losses = 3
        mock_stats_1.games_played = 15
        mock_stats_1.total_points_for = 1500
        mock_stats_1.total_points_against = 1400
        mock_stats_1.team.name = "Team A"

        mock_stats_2 = MagicMock()
        mock_stats_2.team_id = 2
        mock_stats_2.wins = 10
        mock_stats_2.losses = 5
        mock_stats_2.games_played = 15
        mock_stats_2.total_points_for = 1450
        mock_stats_2.total_points_against = 1450
        mock_stats_2.team.name = "Team B"

        mock_session.query.return_value.join.return_value.filter.return_value.options.return_value.all.return_value = [
            mock_stats_1,
            mock_stats_2,
        ]

        standings = stats_service.get_team_standings()

        assert len(standings) == 2
        # Leader should have None for games back
        assert standings[0]["games_back"] is None

        # Second place: ((12 - 10) + (5 - 3)) / 2 = (2 + 2) / 2 = 2.0
        assert standings[1]["games_back"] == 2.0

    def test_get_team_standings_empty_when_no_games(self, stats_service, mock_session):
        """Test that empty standings are returned when no games exist."""
        # Mock no latest game
        mock_session.query.return_value.order_by.return_value.first.return_value = None

        standings = stats_service.get_team_standings()

        assert standings == []
