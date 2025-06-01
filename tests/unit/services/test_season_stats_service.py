"""Unit tests for the season statistics service."""

import datetime
from unittest.mock import MagicMock

import pytest

from app.data_access.models import PlayerGameStats, PlayerSeasonStats
from app.services.season_stats_service import SeasonStatsService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def season_stats_service(mock_db_session):
    """Create a season stats service instance."""
    return SeasonStatsService(mock_db_session)


class TestSeasonStatsService:
    """Test cases for SeasonStatsService."""

    def test_get_season_from_date_october(self, season_stats_service):
        """Test getting season from a date in October."""
        date = datetime.date(2024, 10, 15)
        assert season_stats_service.get_season_from_date(date) == "2024-2025"

    def test_get_season_from_date_january(self, season_stats_service):
        """Test getting season from a date in January."""
        date = datetime.date(2025, 1, 15)
        assert season_stats_service.get_season_from_date(date) == "2024-2025"

    def test_get_season_from_date_september(self, season_stats_service):
        """Test getting season from a date in September."""
        date = datetime.date(2024, 9, 15)
        assert season_stats_service.get_season_from_date(date) == "2023-2024"

    def test_update_player_season_stats_no_games(self, season_stats_service, mock_db_session):
        """Test updating player season stats when no games exist."""
        # Mock query to return no games
        mock_query = MagicMock()
        mock_query.all.return_value = []
        # Handle the chained filter calls
        mock_filter = MagicMock()
        mock_filter.filter.return_value = mock_query
        mock_db_session.query.return_value.join.return_value.filter.return_value = mock_filter

        result = season_stats_service.update_player_season_stats(1, "2024-2025")
        assert result is None

    def test_update_player_season_stats_creates_new(self, season_stats_service, mock_db_session):
        """Test creating new player season stats."""
        # Mock game stats
        game_stats = [
            MagicMock(
                game_id=1, fouls=2, total_ftm=5, total_fta=6, total_2pm=8, total_2pa=10, total_3pm=3, total_3pa=5
            ),
            MagicMock(game_id=2, fouls=3, total_ftm=4, total_fta=5, total_2pm=7, total_2pa=9, total_3pm=2, total_3pa=4),
        ]

        # Mock game for date lookup
        mock_game = MagicMock(date=datetime.date(2024, 11, 1))

        # Configure different query paths
        # For PlayerGameStats query
        mock_game_stats_query = MagicMock()
        mock_game_stats_query.all.return_value = game_stats

        # For PlayerSeasonStats query
        mock_season_stats_query = MagicMock()
        mock_season_stats_query.first.return_value = None

        # Set up query mock to return different things based on what's queried
        def query_side_effect(model):
            if model == PlayerGameStats:
                query = MagicMock()
                query.join.return_value.filter.return_value = mock_game_stats_query
                return query
            elif model == PlayerSeasonStats:
                query = MagicMock()
                query.filter_by.return_value = mock_season_stats_query
                return query
            else:  # For Game.get()
                query = MagicMock()
                query.get.return_value = mock_game
                return query

        mock_db_session.query.side_effect = query_side_effect

        result = season_stats_service.update_player_season_stats(1, "2024-2025")

        # Verify new season stats was added
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # Check that a PlayerSeasonStats object was created and returned
        assert isinstance(result, PlayerSeasonStats)
        assert result.player_id == 1
        assert result.season == "2024-2025"

        # Verify that the object passed to add() was a PlayerSeasonStats
        added_obj = mock_db_session.add.call_args[0][0]
        assert isinstance(added_obj, PlayerSeasonStats)
        assert added_obj.player_id == 1
        assert added_obj.season == "2024-2025"

    def test_get_player_rankings_ppg(self, season_stats_service, mock_db_session):
        """Test getting player rankings by points per game."""
        # Mock latest game for season detection
        mock_game = MagicMock(date=datetime.date(2024, 11, 1))
        mock_db_session.query.return_value.order_by.return_value.first.return_value = mock_game

        # Mock player season stats
        mock_player1 = MagicMock()
        mock_player1.name = "Player 1"
        mock_team1 = MagicMock()
        mock_team1.name = "Team A"
        mock_player1.team = mock_team1

        mock_player2 = MagicMock()
        mock_player2.name = "Player 2"
        mock_team2 = MagicMock()
        mock_team2.name = "Team B"
        mock_player2.team = mock_team2

        stats1 = MagicMock(player_id=1, player=mock_player1, games_played=10, total_ftm=50, total_2pm=100, total_3pm=30)

        stats2 = MagicMock(player_id=2, player=mock_player2, games_played=10, total_ftm=40, total_2pm=80, total_3pm=20)

        mock_query = MagicMock()
        mock_query.all.return_value = [stats1, stats2]
        (
            mock_db_session.query.return_value.join.return_value.join.return_value.filter.return_value.options.return_value
        ) = mock_query

        rankings = season_stats_service.get_player_rankings("ppg", limit=2)

        assert len(rankings) == 2
        assert rankings[0]["rank"] == 1
        assert rankings[0]["player_id"] == 1
        assert rankings[0]["value"] == 34.0  # (50 + 200 + 90) / 10
        assert rankings[1]["rank"] == 2
        assert rankings[1]["player_id"] == 2
        assert rankings[1]["value"] == 26.0  # (40 + 160 + 60) / 10 = 260/10

    def test_get_team_standings(self, season_stats_service, mock_db_session):
        """Test getting team standings."""
        # Mock latest game
        mock_game = MagicMock(date=datetime.date(2024, 11, 1))
        mock_db_session.query.return_value.order_by.return_value.first.return_value = mock_game

        # Mock teams
        team1 = MagicMock()
        team1.name = "Team A"
        team2 = MagicMock()
        team2.name = "Team B"

        # Mock team season stats
        stats1 = MagicMock(
            team_id=1, team=team1, games_played=20, wins=15, losses=5, total_points_for=1600, total_points_against=1400
        )

        stats2 = MagicMock(
            team_id=2, team=team2, games_played=20, wins=10, losses=10, total_points_for=1500, total_points_against=1500
        )

        mock_query_result = [stats1, stats2]
        (
            mock_db_session.query.return_value.join.return_value.filter.return_value.options.return_value.all.return_value
        ) = mock_query_result

        standings = season_stats_service.get_team_standings()

        assert len(standings) == 2
        assert standings[0]["rank"] == 1
        assert standings[0]["team_id"] == 1
        assert standings[0]["wins"] == 15
        assert standings[0]["losses"] == 5
        assert standings[0]["win_pct"] == 0.75
        assert standings[0]["games_back"] is None
        assert standings[1]["rank"] == 2
        assert standings[1]["team_id"] == 2
        assert standings[1]["games_back"] == 5.0  # ((15-10) + (10-5)) / 2 = 10/2 = 5.0

    # Note: Complex workflow tests (update_player_season_stats_updates_existing
    # and update_team_season_stats_calculates_wins_losses) have been removed
    # in favor of simpler integration tests that follow KISS principles.
    #
    # These tests required overly complex mocking that was harder to maintain
    # than the actual code. The functionality is thoroughly covered by:
    # - tests/integration/test_season_statistics.py::test_update_season_stats_integration
    # - tests/integration/test_season_statistics.py::test_player_rankings_integration
    # - tests/integration/test_season_statistics.py::test_team_standings_integration
