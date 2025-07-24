"""Unit tests for awards_service_v2 (PlayerAward table implementation)."""

from datetime import date
from unittest.mock import Mock, patch

from app.services.awards_service_v2 import (
    calculate_player_of_the_week_v2,
    get_current_season,
    get_player_potw_summary,
    get_season_from_date,
    migrate_legacy_awards_to_v2,
)


class TestSeasonHelpersV2:
    """Test season utility functions for v2 service."""

    def test_get_season_from_date(self):
        """Test converting date to season string."""
        assert get_season_from_date(date(2024, 1, 15)) == "2024"
        assert get_season_from_date(date(2024, 12, 31)) == "2024"
        assert get_season_from_date(date(2025, 6, 15)) == "2025"

    @patch("app.services.awards_service_v2.date")
    def test_get_current_season(self, mock_date):
        """Test getting current season."""
        mock_date.today.return_value = date(2024, 7, 15)
        assert get_current_season() == "2024"


class TestCalculatePlayerOfTheWeekV2:
    """Test POTW calculation using PlayerAward table."""

    def test_calculate_all_seasons_v2(self, unit_db_session):
        """Test calculating awards for all seasons using v2."""
        # Create test data
        from tests.unit.services.test_awards_service import create_test_data

        test_data = create_test_data(unit_db_session)

        with patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = [
                test_data["game1"],  # 2024-01-01
                test_data["game2"],  # 2024-01-08
                test_data["game3"],  # 2025-01-01
            ]

            results = calculate_player_of_the_week_v2(unit_db_session)

            assert "2024" in results
            assert "2025" in results
            assert results["2024"] >= 1
            assert results["2025"] >= 1

    def test_calculate_specific_season_v2(self, unit_db_session):
        """Test calculating awards for specific season using v2."""
        from tests.unit.services.test_awards_service import create_test_data

        test_data = create_test_data(unit_db_session)

        with patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = [
                test_data["game1"],  # 2024-01-01
                test_data["game2"],  # 2024-01-08
            ]

            results = calculate_player_of_the_week_v2(unit_db_session, season="2024")

            assert "2024" in results
            assert "2025" not in results

    def test_calculate_with_recalculate_v2(self, unit_db_session):
        """Test recalculation with v2 service."""
        with (
            patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service_v2.delete_all_awards_by_type") as mock_delete,
        ):
            mock_get_games.return_value = []
            mock_delete.return_value = 5

            results = calculate_player_of_the_week_v2(unit_db_session, recalculate=True)

            mock_delete.assert_called_once_with(unit_db_session, "player_of_the_week")
            assert results == {}

    def test_calculate_no_games_v2(self, unit_db_session):
        """Test calculation when no games exist using v2."""
        with patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = []

            results = calculate_player_of_the_week_v2(unit_db_session)

            assert results == {}


class TestGetPlayerPotwSummary:
    """Test getting comprehensive POTW summary."""

    def test_get_player_potw_summary_with_awards(self, unit_db_session, shared_test_player):
        """Test getting summary for player with awards."""
        with (
            patch("app.services.awards_service_v2.get_current_season") as mock_current,
            patch("app.services.awards_service_v2.get_player_award_counts_by_season") as mock_counts,
            patch("app.services.awards_service_v2.get_player_awards_by_type") as mock_recent,
        ):
            mock_current.return_value = "2024"
            mock_counts.return_value = {"2024": 2, "2023": 1}

            # Mock recent awards
            mock_award = Mock()
            mock_award.season = "2024"
            mock_award.week_date = date(2024, 1, 1)
            mock_award.points_scored = 30
            mock_award.created_at = date(2024, 1, 2)
            mock_recent.return_value = [mock_award]

            summary = get_player_potw_summary(unit_db_session, shared_test_player.id)

            assert summary["current_season_count"] == 2
            assert summary["total_count"] == 3
            assert summary["awards_by_season"] == {"2024": 2, "2023": 1}
            assert len(summary["recent_awards"]) == 1
            assert summary["recent_awards"][0]["season"] == "2024"
            assert summary["recent_awards"][0]["points_scored"] == 30

    def test_get_player_potw_summary_no_awards(self, unit_db_session, shared_test_player):
        """Test getting summary for player with no awards."""
        with (
            patch("app.services.awards_service_v2.get_current_season") as mock_current,
            patch("app.services.awards_service_v2.get_player_award_counts_by_season") as mock_counts,
            patch("app.services.awards_service_v2.get_player_awards_by_type") as mock_recent,
        ):
            mock_current.return_value = "2024"
            mock_counts.return_value = {}
            mock_recent.return_value = []

            summary = get_player_potw_summary(unit_db_session, shared_test_player.id)

            assert summary["current_season_count"] == 0
            assert summary["total_count"] == 0
            assert summary["awards_by_season"] == {}
            assert summary["recent_awards"] == []


class TestMigrateLegacyAwards:
    """Test migrating legacy awards to PlayerAward table."""

    def test_migrate_legacy_awards_success(self, unit_db_session):
        """Test successful migration of legacy awards."""
        # Create mock players with legacy awards
        mock_player1 = Mock()
        mock_player1.id = 1
        mock_player1.name = "Player 1"
        mock_player1.player_of_the_week_awards = 3

        mock_player2 = Mock()
        mock_player2.id = 2
        mock_player2.name = "Player 2"
        mock_player2.player_of_the_week_awards = 1

        with (
            patch.object(unit_db_session, "query") as mock_query,
            patch("app.services.awards_service_v2.get_current_season") as mock_current,
            patch("app.services.awards_service_v2.get_awards_by_week") as mock_existing,
            patch("app.services.awards_service_v2.create_player_award") as mock_create,
        ):
            mock_query.return_value.filter.return_value.all.return_value = [mock_player1, mock_player2]
            mock_current.return_value = "2024"
            mock_existing.return_value = []  # No existing awards

            stats = migrate_legacy_awards_to_v2(unit_db_session)

            assert stats["players_processed"] == 2
            assert stats["legacy_awards_found"] == 4
            assert stats["records_created"] == 4
            assert stats["errors"] == 0

            # Should create 3 awards for player1 + 1 for player2
            assert mock_create.call_count == 4

    def test_migrate_legacy_awards_with_errors(self, unit_db_session):
        """Test migration with some errors."""
        mock_player = Mock()
        mock_player.id = 1
        mock_player.name = "Player 1"
        mock_player.player_of_the_week_awards = 2

        with (
            patch.object(unit_db_session, "query") as mock_query,
            patch("app.services.awards_service_v2.get_current_season") as mock_current,
            patch("app.services.awards_service_v2.get_awards_by_week") as mock_existing,
            patch("app.services.awards_service_v2.create_player_award") as mock_create,
        ):
            mock_query.return_value.filter.return_value.all.return_value = [mock_player]
            mock_current.return_value = "2024"
            mock_existing.return_value = []
            mock_create.side_effect = [None, Exception("Test error")]

            stats = migrate_legacy_awards_to_v2(unit_db_session)

            assert stats["players_processed"] == 1
            assert stats["legacy_awards_found"] == 2
            assert stats["errors"] == 1

    def test_migrate_legacy_awards_no_players(self, unit_db_session):
        """Test migration when no players have legacy awards."""
        with patch.object(unit_db_session, "query") as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = []

            stats = migrate_legacy_awards_to_v2(unit_db_session)

            assert stats["players_processed"] == 0
            assert stats["legacy_awards_found"] == 0
            assert stats["records_created"] == 0
            assert stats["errors"] == 0


class TestWeekCalculationV2:
    """Test week-based calculation logic for v2."""

    def test_week_grouping_v2(self, unit_db_session):
        """Test that games are properly grouped by week in v2."""
        from tests.unit.services.test_awards_service import create_test_data

        test_data = create_test_data(unit_db_session)

        # Create games on different days of the same week
        game1 = test_data["game1"]  # Monday
        game1.date = date(2024, 1, 1)  # Monday

        game2 = test_data["game2"]  # Same week (Sunday)
        game2.date = date(2024, 1, 7)  # Sunday

        with patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = [game1, game2]

            results = calculate_player_of_the_week_v2(unit_db_session)

            # Should give only 1 award since both games are in same week
            assert sum(results.values()) == 1

    def test_different_weeks_v2(self, unit_db_session):
        """Test games in different weeks get separate awards in v2."""
        from tests.unit.services.test_awards_service import create_test_data

        test_data = create_test_data(unit_db_session)

        # Create games in different weeks
        game1 = test_data["game1"]
        game1.date = date(2024, 1, 1)  # Week 1

        game2 = test_data["game2"]
        game2.date = date(2024, 1, 8)  # Week 2 (Monday of next week)

        with patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = [game1, game2]

            results = calculate_player_of_the_week_v2(unit_db_session)

            # Should give 2 awards since games are in different weeks
            assert sum(results.values()) == 2


class TestPlayerAwardIntegration:
    """Test integration between v2 service and PlayerAward table."""

    def test_awards_create_player_award_records(self, unit_db_session):
        """Test that v2 calculation creates PlayerAward records."""
        from tests.unit.services.test_awards_service import create_test_data

        test_data = create_test_data(unit_db_session)

        with (
            patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service_v2.create_player_award") as mock_create,
        ):
            mock_get_games.return_value = [test_data["game1"]]

            calculate_player_of_the_week_v2(unit_db_session)

            # Should create PlayerAward record
            mock_create.assert_called()
            call_args = mock_create.call_args[1]  # Get keyword arguments
            assert call_args["award_type"] == "player_of_the_week"
            assert "season" in call_args
            assert "week_date" in call_args
            assert "points_scored" in call_args

    def test_awards_skip_existing_weeks(self, unit_db_session):
        """Test that v2 skips weeks that already have awards."""
        from tests.unit.services.test_awards_service import create_test_data

        test_data = create_test_data(unit_db_session)

        with (
            patch("app.services.awards_service_v2.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service_v2.get_awards_by_week") as mock_existing,
            patch("app.services.awards_service_v2.create_player_award") as mock_create,
        ):
            mock_get_games.return_value = [test_data["game1"]]
            mock_existing.return_value = [Mock()]  # Existing award

            results = calculate_player_of_the_week_v2(unit_db_session, recalculate=False)

            # Should not create new award, but count existing one
            mock_create.assert_not_called()
            assert sum(results.values()) == 1  # Count existing award
