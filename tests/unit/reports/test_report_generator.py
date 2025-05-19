"""
Test module for the ReportGenerator.
"""

from unittest.mock import MagicMock, patch

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

        return {
            "game": game,
            "player_game_stats": player_game_stats,
            "teams": [team_a, team_b],
            "players": [player_a1, player_a2, player_b1, player_b2],
        }

    @pytest.fixture
    def mock_quarter_stats(self):
        """Mock quarter stats data."""
        # Create quarter stats matching the overall game stats
        return [
            # For player 1
            MagicMock(id=1, player_game_stats_id=1, quarter=1, ftm=1, fta=2, fg2m=2, fg2a=4, fg3m=1, fg3a=2),
            MagicMock(id=2, player_game_stats_id=1, quarter=2, ftm=2, fta=2, fg2m=3, fg2a=4, fg3m=1, fg3a=3),
            # For player 2 (similar pattern)
            MagicMock(id=3, player_game_stats_id=2, quarter=1, ftm=0, fta=1, fg2m=2, fg2a=3, fg3m=0, fg3a=1),
            MagicMock(id=4, player_game_stats_id=2, quarter=2, ftm=1, fta=1, fg2m=2, fg2a=3, fg3m=1, fg3a=2),
        ]

    @pytest.fixture
    def mock_crud_modules(self, mock_game_data, mock_quarter_stats):
        """Mock the CRUD modules used by ReportGenerator."""
        # Mock each CRUD module
        mocked_crud_game = MagicMock()
        mocked_crud_team = MagicMock()
        mocked_crud_player = MagicMock()
        mocked_crud_player_game_stats = MagicMock()
        mocked_crud_player_quarter_stats = MagicMock()

        # Set up return values
        mocked_crud_game.get_game_by_id.side_effect = lambda session, game_id: (
            mock_game_data["game"] if game_id == 1 else None
        )

        mocked_crud_team.get_team_by_id.side_effect = lambda session, team_id: (
            mock_game_data["teams"][0] if team_id == 1 else mock_game_data["teams"][1] if team_id == 2 else None
        )

        mocked_crud_player.get_player_by_id.side_effect = lambda session, player_id: (
            next((p for p in mock_game_data["players"] if p.id == player_id), None)
        )

        mocked_crud_player_game_stats.get_player_game_stats_by_game.side_effect = lambda session, game_id: (
            mock_game_data["player_game_stats"] if game_id == 1 else []
        )

        mocked_crud_player_quarter_stats.get_player_quarter_stats.side_effect = lambda session, pgs_id: (
            [qs for qs in mock_quarter_stats if qs.player_game_stats_id == pgs_id]
        )

        return {
            "crud_game": mocked_crud_game,
            "crud_team": mocked_crud_team,
            "crud_player": mocked_crud_player,
            "crud_player_game_stats": mocked_crud_player_game_stats,
            "crud_player_quarter_stats": mocked_crud_player_quarter_stats,
        }

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

    def test_init(self, mock_db_session, mock_stats_calculator):
        """Test initializing the report generator."""
        report_generator = ReportGenerator(mock_db_session, mock_stats_calculator)
        assert report_generator.db_session == mock_db_session
        assert report_generator.stats_calculator == mock_stats_calculator

    @patch("app.reports.report_generator.crud_game")
    @patch("app.reports.report_generator.crud_team")
    @patch("app.reports.report_generator.crud_player")
    @patch("app.reports.report_generator.crud_player_game_stats")
    @patch("app.reports.report_generator.crud_player_quarter_stats")
    def test_get_game_box_score_data(
        self,
        mock_crud_pqs,
        mock_crud_pgs,
        mock_crud_player,
        mock_crud_team,
        mock_crud_game,
        mock_db_session,
        mock_stats_calculator,
        mock_game_data,
        mock_quarter_stats,
    ):
        """Test getting game box score data."""
        # Set up the CRUD mocks
        mock_crud_game.get_game_by_id.return_value = mock_game_data["game"]
        mock_crud_team.get_team_by_id.side_effect = lambda session, team_id: (
            mock_game_data["teams"][0] if team_id == 1 else mock_game_data["teams"][1] if team_id == 2 else None
        )
        mock_crud_player.get_player_by_id.side_effect = lambda session, player_id: (
            next((p for p in mock_game_data["players"] if p.id == player_id), None)
        )
        mock_crud_pgs.get_player_game_stats_by_game.return_value = mock_game_data["player_game_stats"]
        mock_crud_pqs.get_player_quarter_stats.side_effect = lambda session, pgs_id: (
            [qs for qs in mock_quarter_stats if qs.player_game_stats_id == pgs_id]
        )

        report_generator = ReportGenerator(mock_db_session, mock_stats_calculator)

        player_stats, game_info = report_generator.get_game_box_score_data(1)

        # Check game info
        assert game_info["date"] == "2025-05-01"
        assert game_info["playing_team"] == "Team A"
        assert game_info["opponent_team"] == "Team B"

        # Check player stats were calculated (checking first player)
        assert len(player_stats) > 0

        # Verify the CRUD calls were made correctly
        mock_crud_game.get_game_by_id.assert_called_once_with(mock_db_session, 1)
        mock_crud_pgs.get_player_game_stats_by_game.assert_called_once_with(mock_db_session, 1)

    @patch("app.reports.report_generator.crud_game")
    def test_get_game_box_score_data_not_found(self, mock_crud_game, mock_db_session, mock_stats_calculator):
        """Test getting game box score data for a non-existent game."""
        # Setup mock to return None for non-existent game
        mock_crud_game.get_game_by_id.return_value = None

        report_generator = ReportGenerator(mock_db_session, mock_stats_calculator)

        # Try to get data for non-existent game
        with pytest.raises(ValueError) as excinfo:
            report_generator.get_game_box_score_data(999)

        assert "Game not found" in str(excinfo.value)
        mock_crud_game.get_game_by_id.assert_called_once_with(mock_db_session, 999)
