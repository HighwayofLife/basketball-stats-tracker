# tests/integration/test_awards_calculation_e2e.py

"""
End-to-end integration tests for awards calculation functionality.
These tests ensure the admin awards calculation button works without errors.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from app.services.awards_service import calculate_all_season_awards, calculate_player_of_the_week


class TestAwardsCalculationEndToEnd:
    """End-to-end tests for awards calculation to prevent UI button errors."""

    def test_weekly_awards_calculation_e2e_mock(self):
        """Test weekly awards calculation end-to-end with mocked data."""
        # Create comprehensive mocked data that includes all required attributes

        # Mock PlayerQuarterStats
        mock_quarter_stat = Mock()
        mock_quarter_stat.quarter = 4
        mock_quarter_stat.q_2pm = 2
        mock_quarter_stat.q_3pm = 1
        mock_quarter_stat.q_ftm = 3

        # Mock PlayerGameStats with ALL required attributes
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.total_2pm = 8
        mock_game_stat.total_2pa = 15
        mock_game_stat.total_3pm = 3
        mock_game_stat.total_3pa = 7
        mock_game_stat.total_ftm = 6
        mock_game_stat.total_fta = 8
        mock_game_stat.fouls = 2  # Critical: correct attribute name
        mock_game_stat.quarter_stats = [mock_quarter_stat]  # Critical: correct relationship name

        # Mock Game
        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)  # Monday
        mock_game.player_game_stats = [mock_game_stat]

        # Mock Player
        mock_player = Mock()
        mock_player.id = 1
        mock_player.name = "Test Player"

        mock_session = Mock()

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service._calculate_week_winners") as mock_week_winners,
            patch("app.services.awards_service.get_awards_by_week") as mock_get_awards,
        ):
            mock_get_games.return_value = [mock_game]
            mock_week_winners.return_value = [1]  # Player ID
            mock_get_awards.return_value = []  # No existing awards

            # This should not raise any AttributeError
            try:
                result = calculate_player_of_the_week(mock_session, season=None, recalculate=False)
                assert isinstance(result, dict)
                print(f"✅ Weekly awards calculation completed: {result}")
            except AttributeError as e:
                pytest.fail(f"❌ AttributeError in weekly awards calculation: {e}")
            except Exception as e:
                pytest.fail(f"❌ Unexpected error in weekly awards calculation: {e}")

    def test_season_awards_calculation_e2e_mock(self):
        """Test season awards calculation end-to-end with mocked data."""
        # Mock PlayerGameStats with ALL required attributes
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.total_2pm = 10
        mock_game_stat.total_2pa = 18
        mock_game_stat.total_3pm = 4
        mock_game_stat.total_3pa = 8
        mock_game_stat.total_ftm = 8
        mock_game_stat.total_fta = 10
        mock_game_stat.fouls = 3  # Critical: correct attribute name (not total_fouls)

        # Mock Game
        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        mock_session = Mock()

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

            # This should not raise any AttributeError
            try:
                result = calculate_all_season_awards(mock_session, season="2024", recalculate=False)
                assert isinstance(result, dict)
                print(f"✅ Season awards calculation completed: {result}")
            except AttributeError as e:
                if "total_fouls" in str(e):
                    pytest.fail(f"❌ 'total_fouls' AttributeError in season awards: {e}")
                else:
                    pytest.fail(f"❌ AttributeError in season awards calculation: {e}")
            except Exception as e:
                pytest.fail(f"❌ Unexpected error in season awards calculation: {e}")

    def test_comprehensive_awards_calculation_flow(self):
        """Test the complete awards calculation flow that the admin UI would execute."""
        mock_session = Mock()

        # Test both weekly and season awards in sequence (like the UI button would)
        try:
            # 1. Calculate weekly awards
            with (
                patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
                patch("app.services.awards_service._calculate_week_winners") as mock_week_winners,
                patch("app.services.awards_service.get_awards_by_week") as mock_get_awards,
            ):
                # Mock minimal data for weekly calculation
                mock_get_games.return_value = []
                mock_week_winners.return_value = []
                mock_get_awards.return_value = []

                weekly_result = calculate_player_of_the_week(mock_session, season="2024", recalculate=False)

            # 2. Calculate season awards
            with (
                patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
                patch("app.services.awards_service.get_season_from_date") as mock_get_season,
                patch("app.data_access.crud.crud_player_award.get_season_awards") as mock_get_awards,
                patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
            ):
                # Mock minimal data for season calculation
                mock_get_games.return_value = []
                mock_get_season.return_value = "2024"
                mock_get_awards.return_value = []
                mock_create_award.return_value = Mock()

                season_result = calculate_all_season_awards(mock_session, season="2024", recalculate=False)

            # Both should complete without errors
            assert isinstance(weekly_result, dict)
            assert isinstance(season_result, dict)
            print("✅ Complete awards calculation flow completed successfully")

        except AttributeError as e:
            pytest.fail(f"❌ AttributeError in comprehensive awards flow: {e}")
        except Exception as e:
            pytest.fail(f"❌ Unexpected error in comprehensive awards flow: {e}")

    def test_calculate_all_season_awards_full_integration(self):
        """Test complete calculate_all_season_awards function integration."""
        # Create comprehensive mock data for all 8 season awards
        mock_stat1 = Mock()
        mock_stat1.player_id = 1
        mock_stat1.total_2pm = 12
        mock_stat1.total_2pa = 20
        mock_stat1.total_3pm = 6
        mock_stat1.total_3pa = 10
        mock_stat1.total_ftm = 10
        mock_stat1.total_fta = 12
        mock_stat1.fouls = 1  # Low fouls for defensive tackle

        mock_stat2 = Mock()
        mock_stat2.player_id = 2
        mock_stat2.total_2pm = 8
        mock_stat2.total_2pa = 18
        mock_stat2.total_3pm = 4
        mock_stat2.total_3pa = 12
        mock_stat2.total_ftm = 6
        mock_stat2.total_fta = 10
        mock_stat2.fouls = 5  # High fouls

        mock_game1 = Mock()
        mock_game1.date = date(2024, 1, 15)
        mock_game1.player_game_stats = [mock_stat1]

        mock_game2 = Mock()
        mock_game2.date = date(2024, 2, 15)
        mock_game2.player_game_stats = [mock_stat2]

        mock_session = Mock()

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service.get_season_from_date") as mock_get_season,
            patch("app.data_access.crud.crud_player_award.get_season_awards") as mock_get_awards,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
        ):
            mock_get_games.return_value = [mock_game1, mock_game2]
            mock_get_season.return_value = "2024"
            mock_get_awards.return_value = []  # No existing awards
            mock_create_award.return_value = Mock()  # Successful creation

            # Test the full integration
            result = calculate_all_season_awards(mock_session, season="2024", recalculate=False)

            # Import the actual season awards configuration to avoid magic numbers
            from app.services.awards_service import SEASON_AWARD_TYPES

            # Verify all season awards were calculated
            expected_awards = SEASON_AWARD_TYPES

            assert isinstance(result, dict)
            for award_type in expected_awards:
                assert award_type in result, f"Missing award type: {award_type}"
                assert isinstance(result[award_type], dict), f"Expected dict for {award_type}: {result[award_type]}"

            # Verify create_player_award_safe was called for each award (may be more than 9 due to ties)
            assert mock_create_award.call_count >= 9

            print(f"✅ Season awards integration test passed: {result}")


class TestModelAttributeConsistency:
    """Tests to ensure model attributes are correctly used across services."""

    def test_player_game_stats_attributes_consistency(self):
        """Verify PlayerGameStats attributes are consistently referenced."""
        from app.data_access.models import PlayerGameStats

        # These are the attributes that should exist
        expected_attributes = [
            "fouls",  # NOT 'total_fouls'
            "total_2pm",
            "total_2pa",
            "total_3pm",
            "total_3pa",
            "total_ftm",
            "total_fta",
        ]

        expected_relationships = [
            "quarter_stats",  # NOT 'player_quarter_stats'
        ]

        for attr in expected_attributes:
            assert hasattr(PlayerGameStats, attr), f"PlayerGameStats missing attribute: {attr}"

        for rel in expected_relationships:
            assert hasattr(PlayerGameStats, rel), f"PlayerGameStats missing relationship: {rel}"

        # These should NOT exist (common mistakes)
        forbidden_attributes = ["total_fouls", "player_quarter_stats"]

        for attr in forbidden_attributes:
            assert not hasattr(PlayerGameStats, attr), f"PlayerGameStats should not have attribute: {attr}"
