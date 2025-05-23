# pylint: disable=protected-access
"""
Test module for the StatsEntryService.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.data_access.models import PlayerGameStats, PlayerQuarterStats
from app.services.stats_entry_service import StatsEntryService


class TestStatsEntryService:
    """Tests for the StatsEntryService."""

    @pytest.fixture
    def mock_input_parser(self):
        """Mock the input parser function."""

        def parse_shot_string(shot_string, _mapping):
            # Return mock parsed stats based on the fixture data
            mock_stats = {
                "22-1x": {"ftm": 1, "fta": 2, "fg2m": 2, "fg2a": 3, "fg3m": 0, "fg3a": 0},
                "3/2": {"ftm": 0, "fta": 0, "fg2m": 1, "fg2a": 1, "fg3m": 1, "fg3a": 2},
                "11": {"ftm": 2, "fta": 2, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},
                "": {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0},
            }
            return mock_stats.get(shot_string, {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0})

        return parse_shot_string

    @pytest.fixture
    def shot_mapping_fixture(self):
        """Provide a shot mapping for testing."""
        return {
            "1": {"type": "FT", "made": True},
            "x": {"type": "FT", "made": False},
            "2": {"type": "2P", "made": True},
            "-": {"type": "2P", "made": False},
            "3": {"type": "3P", "made": True},
            "/": {"type": "3P", "made": False},
        }

    def test_init(self, db_session, mock_input_parser, shot_mapping_fixture):
        """Test initializing the stats entry service."""
        service = StatsEntryService(db_session, mock_input_parser, shot_mapping_fixture)

        assert service._db_session == db_session
        assert service._parse_shot_string == mock_input_parser
        assert service._shot_mapping == shot_mapping_fixture

    def test_record_player_game_performance(self, db_session, mock_input_parser, shot_mapping_fixture):
        """Test recording a player's game performance."""
        # Mock the CRUD functions
        mock_create_player_game_stats = MagicMock(return_value=PlayerGameStats(id=1, game_id=1, player_id=1, fouls=2))
        mock_create_player_quarter_stats = MagicMock(
            return_value=PlayerQuarterStats(
                id=1, player_game_stat_id=1, quarter_number=1, ftm=1, fta=2, fg2m=2, fg2a=3, fg3m=0, fg3a=0
            )
        )
        mock_update_player_game_stats_totals = MagicMock(
            return_value=PlayerGameStats(
                id=1,
                game_id=1,
                player_id=1,
                fouls=2,
                total_ftm=3,
                total_fta=4,
                total_2pm=3,
                total_2pa=4,
                total_3pm=1,
                total_3pa=2,
            )
        )

        with (
            patch("app.services.stats_entry_service.create_player_game_stats", mock_create_player_game_stats),
            patch("app.services.stats_entry_service.create_player_quarter_stats", mock_create_player_quarter_stats),
            patch(
                "app.services.stats_entry_service.update_player_game_stats_totals",
                mock_update_player_game_stats_totals,
            ),
        ):
            service = StatsEntryService(db_session, mock_input_parser, shot_mapping_fixture)

            # Record performance with quarter shot strings
            result = service.record_player_game_performance(
                game_id=1, player_id=1, fouls=2, quarter_shot_strings=["22-1x", "3/2", "11", ""]
            )

            # Verify result
            assert result.id == 1
            assert result.game_id == 1
            assert result.player_id == 1
            assert result.fouls == 2
            assert result.total_ftm == 3
            assert result.total_fta == 4
            assert result.total_2pm == 3
            assert result.total_2pa == 4
            assert result.total_3pm == 1
            assert result.total_3pa == 2

            # Verify CRUD function calls
            mock_create_player_game_stats.assert_called_once_with(db_session, game_id=1, player_id=1, fouls=2)

            # Should be called 4 times, once for each quarter
            assert mock_create_player_quarter_stats.call_count == 4

            # Verify the update totals call
            mock_update_player_game_stats_totals.assert_called_once()
            args, kwargs = mock_update_player_game_stats_totals.call_args
            assert args[0] == db_session
            assert kwargs["player_game_stat_id"] == 1
            assert "totals" in kwargs
            totals = kwargs["totals"]
            assert totals["total_ftm"] == 3
            assert totals["total_fta"] == 4
            assert totals["total_2pm"] == 3
            assert totals["total_2pa"] == 4
            assert totals["total_3pm"] == 1
            assert totals["total_3pa"] == 2

    def test_record_player_game_performance_empty_quarters(self, db_session, mock_input_parser, shot_mapping_fixture):
        """Test recording a player's game performance with empty quarter strings."""
        # Mock the CRUD functions
        mock_create_player_game_stats = MagicMock(return_value=PlayerGameStats(id=1, game_id=1, player_id=1, fouls=0))
        mock_create_player_quarter_stats = MagicMock(
            return_value=PlayerQuarterStats(
                id=1, player_game_stat_id=1, quarter_number=1, ftm=0, fta=0, fg2m=0, fg2a=0, fg3m=0, fg3a=0
            )
        )
        mock_update_player_game_stats_totals = MagicMock(
            return_value=PlayerGameStats(
                id=1,
                game_id=1,
                player_id=1,
                fouls=0,
                total_ftm=0,
                total_fta=0,
                total_2pm=0,
                total_2pa=0,
                total_3pm=0,
                total_3pa=0,
            )
        )

        with (
            patch("app.services.stats_entry_service.create_player_game_stats", mock_create_player_game_stats),
            patch("app.services.stats_entry_service.create_player_quarter_stats", mock_create_player_quarter_stats),
            patch(
                "app.services.stats_entry_service.update_player_game_stats_totals", mock_update_player_game_stats_totals
            ),
        ):
            service = StatsEntryService(db_session, mock_input_parser, shot_mapping_fixture)

            # Record performance with empty quarter shot strings
            result = service.record_player_game_performance(
                game_id=1, player_id=1, fouls=0, quarter_shot_strings=["", "", "", ""]
            )

            # Verify result has all zeros for stats
            assert result.total_ftm == 0
            assert result.total_fta == 0
            assert result.total_2pm == 0
            assert result.total_2pa == 0
            assert result.total_3pm == 0
            assert result.total_3pa == 0

            # Should still create quarter stats entries
            assert mock_create_player_quarter_stats.call_count == 4
