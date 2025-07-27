# tests/integration/test_awards_integration_simple.py

"""
Simple integration tests for awards functionality.
These tests verify the awards system works with mocked data.
"""

from datetime import date
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from app.cli import cli
from app.services.awards_service import calculate_all_season_awards, calculate_dub_club, calculate_player_of_the_week


class TestAwardsIntegrationSimple:
    """Simple integration tests for awards calculation."""

    def test_calculate_potw_with_mock_data(self):
        """Test POTW calculation with mocked database data."""
        mock_session = Mock()

        # Mock player stats data
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.total_2pm = 8
        mock_game_stat.total_2pa = 15
        mock_game_stat.total_3pm = 3
        mock_game_stat.total_3pa = 7
        mock_game_stat.total_ftm = 6
        mock_game_stat.total_fta = 8
        mock_game_stat.fouls = 2

        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        # Mock player for the award creation
        mock_player = Mock()
        mock_player.id = 1
        mock_player.name = "Test Player"

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service.crud_player.get_player_by_id") as mock_get_player,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
            patch("app.services.awards_service.get_awards_by_week") as mock_get_awards,
        ):
            mock_get_games.return_value = [mock_game]
            mock_get_player.return_value = mock_player
            mock_create_award.return_value = Mock()  # Successful award creation
            mock_get_awards.return_value = [Mock()]  # One award created

            # Should complete without errors
            result = calculate_player_of_the_week(mock_session, season="2024", recalculate=False)

            assert isinstance(result, dict)
            assert result == {"2024": 1}  # One award given

            # Verify the award was attempted to be created
            mock_create_award.assert_called_once()

    def test_calculate_all_season_awards_with_mock_data(self):
        """Test season awards calculation with mocked database data."""
        mock_session = Mock()

        # Mock player stats data
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.total_2pm = 10
        mock_game_stat.total_2pa = 18
        mock_game_stat.total_3pm = 4
        mock_game_stat.total_3pa = 8
        mock_game_stat.total_ftm = 8
        mock_game_stat.total_fta = 10
        mock_game_stat.fouls = 3

        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service.get_season_from_date") as mock_get_season,
            patch("app.data_access.crud.crud_player_award.get_season_awards") as mock_get_awards,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
        ):
            mock_get_games.return_value = [mock_game]
            mock_get_season.return_value = "2024"
            mock_get_awards.return_value = []  # No existing awards
            mock_create_award.return_value = Mock()  # Successful creation

            # Should complete without errors
            result = calculate_all_season_awards(mock_session, season="2024", recalculate=False)

            assert isinstance(result, dict)
            # Should have calculated all 8 season awards
            expected_awards = [
                "top_scorer",
                "sharpshooter",
                "efficiency_expert",
                "charity_stripe_regular",
                "human_highlight_reel",
                "defensive_tackle",
                "air_ball_artist",
                "air_assault",
            ]
            for award_type in expected_awards:
                assert award_type in result

            # Should have called create_player_award_safe for each award
            assert mock_create_award.call_count >= 8

    def test_calculate_dub_club_integration(self):
        """Test Dub Club calculation with mocked database data."""
        mock_session = Mock()

        # Create mock game with multiple players
        mock_game_stat1 = Mock()
        mock_game_stat1.player_id = 1
        mock_game_stat1.total_2pm = 10  # 20 points
        mock_game_stat1.total_3pm = 0
        mock_game_stat1.total_ftm = 0

        mock_game_stat2 = Mock()
        mock_game_stat2.player_id = 2
        mock_game_stat2.total_2pm = 8  # 25 points
        mock_game_stat2.total_3pm = 3
        mock_game_stat2.total_ftm = 0

        mock_game_stat3 = Mock()
        mock_game_stat3.player_id = 3
        mock_game_stat3.total_2pm = 9  # 18 points (should not get award)
        mock_game_stat3.total_3pm = 0
        mock_game_stat3.total_ftm = 0

        mock_game = Mock()
        mock_game.id = 1
        mock_game.date = date(2024, 1, 15)  # Monday
        mock_game.player_game_stats = [mock_game_stat1, mock_game_stat2, mock_game_stat3]

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
            patch("app.services.awards_service.get_awards_by_week") as mock_get_awards,
        ):
            mock_get_games.return_value = [mock_game]
            mock_awards = [Mock(), Mock()]  # Two awards created
            mock_create_award.side_effect = mock_awards
            mock_get_awards.return_value = mock_awards

            result = calculate_dub_club(mock_session, season=None, recalculate=False)

            # Should create awards for players 1 and 2 (20+ points)
            assert mock_create_award.call_count == 2
            assert result == {"2024": 2}


class TestNewAwardsIntegration:
    """Integration tests for new award calculations."""

    def test_calculate_marksman_award_integration(self, integration_db_session):
        """Test Marksman Award calculation integration."""
        session = integration_db_session

        from app.services.awards_service import calculate_marksman_award

        results = calculate_marksman_award(session, season="2024", recalculate=False)

        # Should process without error and return season-keyed results
        assert isinstance(results, dict)
        # Note: May be empty if no games exist in test database

    def test_calculate_perfect_performance_integration(self, integration_db_session):
        """Test Perfect Performance Award calculation integration."""
        session = integration_db_session

        from app.services.awards_service import calculate_perfect_performance

        results = calculate_perfect_performance(session, season="2024", recalculate=False)

        # Should process without error and return season-keyed results
        assert isinstance(results, dict)
        # Note: May be empty if no games exist in test database

    def test_calculate_breakout_performance_integration(self, integration_db_session):
        """Test Breakout Performance Award calculation integration."""
        session = integration_db_session

        from app.services.awards_service import calculate_breakout_performance

        results = calculate_breakout_performance(session, season="2024", recalculate=False)

        # Should process without error and return season-keyed results
        assert isinstance(results, dict)
        # Note: May be empty if no games exist in test database

    def test_calculate_all_weekly_awards_includes_new_awards(self, integration_db_session):
        """Test that calculate_all_weekly_awards includes the new awards."""
        session = integration_db_session

        from app.services.awards_service import calculate_all_weekly_awards

        results = calculate_all_weekly_awards(session, season="2024", recalculate=False)

        # Should include all new awards
        assert "marksman_award" in results
        assert "perfect_performance" in results
        assert "breakout_performance" in results

        # Each should return a dict with season keys
        for award_type in ["marksman_award", "perfect_performance", "breakout_performance"]:
            assert isinstance(results[award_type], dict)


class TestAwardsCLIIntegrationSimple:
    """Simple CLI integration tests for awards commands."""

    def test_cli_calculate_potw_basic(self):
        """Test basic CLI command execution."""
        runner = CliRunner()

        with (
            patch("app.dependencies.get_db") as mock_get_db,
            patch("app.services.awards_service.calculate_player_of_the_week") as mock_calc,
        ):
            mock_session = Mock()
            mock_get_db.return_value = iter([mock_session])
            mock_calc.return_value = {"2024": 3}

            result = runner.invoke(cli, ["calculate-potw"])

            assert result.exit_code == 0
            assert "Awards calculated successfully!" in result.output
            assert "2024: 3 awards" in result.output
            assert "Total awards given: 3" in result.output
            mock_calc.assert_called_once_with(mock_session, season=None, recalculate=False)

    def test_cli_calculate_potw_with_season(self):
        """Test CLI command with season parameter."""
        runner = CliRunner()

        with (
            patch("app.dependencies.get_db") as mock_get_db,
            patch("app.services.awards_service.calculate_player_of_the_week") as mock_calc,
        ):
            mock_session = Mock()
            mock_get_db.return_value = iter([mock_session])
            mock_calc.return_value = {"2024": 2}

            result = runner.invoke(cli, ["calculate-potw", "--season", "2024"])

            assert result.exit_code == 0
            assert "2024: 2 awards" in result.output
            mock_calc.assert_called_once_with(mock_session, season="2024", recalculate=False)

    def test_cli_calculate_potw_with_recalculate(self):
        """Test CLI command with recalculate flag."""
        runner = CliRunner()

        with (
            patch("app.dependencies.get_db") as mock_get_db,
            patch("app.services.awards_service.calculate_player_of_the_week") as mock_calc,
        ):
            mock_session = Mock()
            mock_get_db.return_value = iter([mock_session])
            mock_calc.return_value = {"2024": 1}

            result = runner.invoke(cli, ["calculate-potw", "--recalculate"])

            assert result.exit_code == 0
            assert "Recalculating all Player of the Week awards" in result.output
            mock_calc.assert_called_once_with(mock_session, season=None, recalculate=True)

    def test_cli_calculate_potw_no_results(self):
        """Test CLI command when no awards are given."""
        runner = CliRunner()

        with (
            patch("app.dependencies.get_db") as mock_get_db,
            patch("app.services.awards_service.calculate_player_of_the_week") as mock_calc,
        ):
            mock_session = Mock()
            mock_get_db.return_value = iter([mock_session])
            mock_calc.return_value = {}

            result = runner.invoke(cli, ["calculate-potw"])

            assert result.exit_code == 0
            assert "No awards were given" in result.output

    def test_cli_calculate_potw_error_handling(self):
        """Test CLI command error handling."""
        runner = CliRunner()

        with (
            patch("app.dependencies.get_db") as mock_get_db,
            patch("app.services.awards_service.calculate_player_of_the_week") as mock_calc,
        ):
            mock_session = Mock()
            mock_get_db.return_value = iter([mock_session])
            mock_calc.side_effect = Exception("Database error")

            result = runner.invoke(cli, ["calculate-potw"])

            assert result.exit_code == 1
            assert "Error calculating awards: Database error" in result.output

    def test_cli_calculate_potw_invalid_season(self):
        """Test CLI command with invalid season format."""
        runner = CliRunner()

        result = runner.invoke(cli, ["calculate-potw", "--season", "invalid"])

        assert result.exit_code == 1
        assert "Season must be a 4-digit year" in result.output
