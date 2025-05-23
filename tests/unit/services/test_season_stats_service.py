"""Unit tests for the season statistics service."""

import datetime
from unittest.mock import MagicMock

import pytest

from app.data_access.models import Game, PlayerGameStats, PlayerSeasonStats, TeamSeasonStats
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
        mock_db_session.query.return_value.join.return_value.filter.return_value = mock_query

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

        # Mock game
        mock_game = MagicMock(date=datetime.date(2024, 11, 1))
        mock_db_session.query.return_value.get.return_value = mock_game

        # Mock query chain
        mock_query = MagicMock()
        mock_query.all.return_value = game_stats
        mock_db_session.query.return_value.join.return_value.filter.return_value = mock_query

        # Mock season stats query to return None (doesn't exist)
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None

        result = season_stats_service.update_player_season_stats(1, "2024-2025")

        # Verify new season stats was added
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # Check the added object
        added_stats = mock_db_session.add.call_args[0][0]
        assert isinstance(added_stats, PlayerSeasonStats)
        assert added_stats.player_id == 1
        assert added_stats.season == "2024-2025"
        assert added_stats.games_played == 2
        assert added_stats.total_fouls == 5
        assert added_stats.total_ftm == 9
        assert added_stats.total_fta == 11
        assert added_stats.total_2pm == 15
        assert added_stats.total_2pa == 19
        assert added_stats.total_3pm == 5
        assert added_stats.total_3pa == 9

    def test_update_player_season_stats_updates_existing(self, season_stats_service, mock_db_session):
        """Test updating existing player season stats."""
        # Mock existing season stats
        existing_stats = MagicMock(spec=PlayerSeasonStats)
        existing_stats.player_id = 1
        existing_stats.season = "2024-2025"

        # Mock game stats
        game_stats = [
            MagicMock(game_id=1, fouls=2, total_ftm=5, total_fta=6, total_2pm=8, total_2pa=10, total_3pm=3, total_3pa=5)
        ]

        # Mock query chain
        mock_query = MagicMock()
        mock_query.all.return_value = game_stats
        mock_db_session.query.return_value.join.return_value.filter.return_value = mock_query

        # Mock season stats query to return existing
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = existing_stats

        result = season_stats_service.update_player_season_stats(1, "2024-2025")

        # Verify stats were updated
        assert existing_stats.games_played == 1
        assert existing_stats.total_fouls == 2
        assert existing_stats.total_ftm == 5
        mock_db_session.commit.assert_called_once()

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
        mock_db_session.query.return_value.join.return_value.join.return_value.filter.return_value.options.return_value = (
            mock_query
        )

        rankings = season_stats_service.get_player_rankings("ppg", limit=2)

        assert len(rankings) == 2
        assert rankings[0]["rank"] == 1
        assert rankings[0]["player_id"] == 1
        assert rankings[0]["value"] == 34.0  # (50 + 200 + 90) / 10
        assert rankings[1]["rank"] == 2
        assert rankings[1]["player_id"] == 2
        assert rankings[1]["value"] == 24.0  # (40 + 160 + 60) / 10

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
        mock_db_session.query.return_value.join.return_value.filter.return_value.options.return_value.all.return_value = (
            mock_query_result
        )

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
        assert standings[1]["games_back"] == 2.5

    def test_update_team_season_stats_calculates_wins_losses(self, season_stats_service, mock_db_session):
        """Test that team season stats correctly calculates wins and losses."""
        team_id = 1

        # Mock games
        game1 = MagicMock(id=1, playing_team_id=1, opponent_team_id=2)
        game2 = MagicMock(id=2, playing_team_id=2, opponent_team_id=1)

        # Mock game query
        games_query = MagicMock()
        games_query.all.return_value = [game1, game2]
        mock_db_session.query.return_value.filter.return_value = games_query

        # Mock player stats for each game
        # Game 1: Team 1 scores 80, Team 2 scores 70 (Team 1 wins)
        team1_game1_stats = [
            MagicMock(total_ftm=10, total_fta=12, total_2pm=20, total_2pa=25, total_3pm=10, total_3pa=15),
            MagicMock(total_ftm=5, total_fta=6, total_2pm=15, total_2pa=20, total_3pm=5, total_3pa=10),
        ]
        team2_game1_stats = [
            MagicMock(total_ftm=8, total_fta=10, total_2pm=18, total_2pa=22, total_3pm=8, total_3pa=12)
        ]

        # Game 2: Team 1 scores 75, Team 2 scores 85 (Team 1 loses)
        team1_game2_stats = [
            MagicMock(total_ftm=8, total_fta=10, total_2pm=18, total_2pa=23, total_3pm=9, total_3pa=14)
        ]
        team2_game2_stats = [
            MagicMock(total_ftm=12, total_fta=14, total_2pm=22, total_2pa=26, total_3pm=9, total_3pa=13)
        ]

        # Mock the query chains for player stats
        def side_effect(*args, **kwargs):
            filter_call = args[0] if args else None
            if hasattr(filter_call, "left") and hasattr(filter_call.left, "value"):
                # Check which query is being made
                game_id = None
                team_id_check = None
                for clause in filter_call.clauses:
                    if hasattr(clause.left, "key") and clause.left.key == "game_id":
                        game_id = clause.right.value
                    if hasattr(clause.left, "key") and clause.left.key == "team_id":
                        team_id_check = clause.right.value

                result = MagicMock()
                if game_id == 1 and team_id_check == 1:
                    result.all.return_value = team1_game1_stats
                elif game_id == 1 and team_id_check == 2:
                    result.all.return_value = team2_game1_stats
                elif game_id == 2 and team_id_check == 1:
                    result.all.return_value = team1_game2_stats
                elif game_id == 2 and team_id_check == 2:
                    result.all.return_value = team2_game2_stats
                else:
                    result.all.return_value = []
                return result

            # Default mock
            result = MagicMock()
            result.all.return_value = []
            return result

        # Create a more sophisticated mock
        player_stats_query = MagicMock()
        player_stats_query.join.return_value.filter.side_effect = side_effect

        # Mock db session query to return our custom query for PlayerGameStats
        def query_side_effect(model):
            if model == Game:
                return MagicMock(filter=MagicMock(return_value=games_query))
            elif model == PlayerGameStats:
                return player_stats_query
            elif model == TeamSeasonStats:
                result = MagicMock()
                result.filter_by.return_value.first.return_value = None
                return result
            return MagicMock()

        mock_db_session.query.side_effect = query_side_effect

        # Call the method
        result = season_stats_service.update_team_season_stats(team_id, "2024-2025")

        # Verify the season stats were created correctly
        assert mock_db_session.add.called
        added_stats = mock_db_session.add.call_args[0][0]
        assert isinstance(added_stats, TeamSeasonStats)
        assert added_stats.games_played == 2
        assert added_stats.wins == 1
        assert added_stats.losses == 1
