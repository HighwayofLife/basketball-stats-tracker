"""
Test module for the scorebook parser utilities.
"""

import pytest

from app.utils.scorebook_parser import (
    calculate_points_from_notation,
    calculate_team_score_from_players,
    format_scoring_notation_help,
    get_shooting_percentages,
    parse_scorebook_entry,
    parse_scoring_notation,
    validate_scoring_notation,
)


class TestParseScoringNotation:
    """Tests for parse_scoring_notation function."""

    def test_empty_notation(self):
        """Test parsing empty notation."""
        result = parse_scoring_notation("")
        expected = {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}
        assert result == expected

    def test_free_throws_only(self):
        """Test parsing notation with only free throws."""
        result = parse_scoring_notation("11x")
        expected = {"ftm": 2, "fta": 3, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}
        assert result == expected

    def test_two_pointers_only(self):
        """Test parsing notation with only 2-point shots."""
        result = parse_scoring_notation("22-")
        expected = {"ftm": 0, "fta": 0, "fg2m": 2, "fg2a": 3, "fg3m": 0, "fg3a": 0}
        assert result == expected

    def test_three_pointers_only(self):
        """Test parsing notation with only 3-point shots."""
        result = parse_scoring_notation("3//")
        expected = {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 1, "fg3a": 3}
        assert result == expected

    def test_mixed_notation(self):
        """Test parsing notation with mixed shot types."""
        result = parse_scoring_notation("22-1x3/")
        expected = {"ftm": 1, "fta": 2, "fg2m": 2, "fg2a": 3, "fg3m": 1, "fg3a": 2}
        assert result == expected

    def test_case_insensitive(self):
        """Test that parsing is case insensitive."""
        result = parse_scoring_notation("11X")
        expected = {"ftm": 2, "fta": 3, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}
        assert result == expected

    def test_with_spaces(self):
        """Test parsing notation with spaces."""
        result = parse_scoring_notation("2 2 - 1 x")
        expected = {"ftm": 1, "fta": 2, "fg2m": 2, "fg2a": 3, "fg3m": 0, "fg3a": 0}
        assert result == expected


class TestCalculatePointsFromNotation:
    """Tests for calculate_points_from_notation function."""

    def test_empty_notation(self):
        """Test calculating points from empty notation."""
        assert calculate_points_from_notation("") == 0

    def test_no_makes(self):
        """Test calculating points when all shots are missed."""
        assert calculate_points_from_notation("x-/") == 0

    def test_free_throws_only(self):
        """Test calculating points from free throws only."""
        assert calculate_points_from_notation("111x") == 3

    def test_two_pointers_only(self):
        """Test calculating points from 2-pointers only."""
        assert calculate_points_from_notation("222-") == 6

    def test_three_pointers_only(self):
        """Test calculating points from 3-pointers only."""
        assert calculate_points_from_notation("33/") == 6

    def test_mixed_scoring(self):
        """Test calculating points from mixed scoring."""
        assert calculate_points_from_notation("22-1x3/") == 8  # 4 + 1 + 3

    def test_complex_notation(self):
        """Test calculating points from complex notation."""
        assert calculate_points_from_notation("321x-/") == 6  # 3 + 2 + 1


class TestValidateScoringNotation:
    """Tests for validate_scoring_notation function."""

    def test_empty_notation(self):
        """Test validating empty notation."""
        is_valid, error = validate_scoring_notation("")
        assert is_valid is True
        assert error == ""

    def test_valid_notation(self):
        """Test validating correct notation."""
        is_valid, error = validate_scoring_notation("22-1x3/")
        assert is_valid is True
        assert error == ""

    def test_valid_with_spaces(self):
        """Test validating notation with spaces."""
        is_valid, error = validate_scoring_notation("2 2 - 1 x")
        assert is_valid is True
        assert error == ""

    def test_invalid_character(self):
        """Test validating notation with invalid character."""
        is_valid, error = validate_scoring_notation("22-1z")
        assert is_valid is False
        assert "Invalid character 'z'" in error

    def test_multiple_invalid_characters(self):
        """Test validating notation with multiple invalid characters."""
        is_valid, error = validate_scoring_notation("22ab")
        assert is_valid is False
        assert "Invalid character" in error


class TestParseScorebookEntry:
    """Tests for parse_scorebook_entry function."""

    def test_valid_entry(self):
        """Test parsing a valid scorebook entry."""
        player_data = {
            "player_id": 123,
            "fouls": 3,
            "qt1_shots": "22-1x",
            "qt2_shots": "3/2",
            "qt3_shots": "11",
            "qt4_shots": "",
        }

        result = parse_scorebook_entry(player_data)

        assert result["player_id"] == 123
        assert result["fouls"] == 3
        assert len(result["quarter_stats"]) == 6

        # Check total stats
        total = result["total_stats"]
        assert total["ftm"] == 3
        assert total["fta"] == 4
        assert total["fg2m"] == 3
        assert total["fg2a"] == 4
        assert total["fg3m"] == 1
        assert total["fg3a"] == 2

    def test_missing_player_id(self):
        """Test parsing entry without player_id."""
        player_data = {"fouls": 2, "qt1_shots": "22"}

        with pytest.raises(ValueError, match="player_id is required"):
            parse_scorebook_entry(player_data)

    def test_missing_fouls(self):
        """Test parsing entry without fouls."""
        player_data = {"player_id": 123, "qt1_shots": "22"}

        with pytest.raises(ValueError, match="fouls is required"):
            parse_scorebook_entry(player_data)

    def test_invalid_notation(self):
        """Test parsing entry with invalid notation."""
        player_data = {"player_id": 123, "fouls": 2, "qt1_shots": "22z"}

        with pytest.raises(ValueError, match="Invalid character"):
            parse_scorebook_entry(player_data)

    def test_all_empty_quarters(self):
        """Test parsing entry with all empty quarters."""
        player_data = {"player_id": 123, "fouls": 0, "qt1_shots": "", "qt2_shots": "", "qt3_shots": "", "qt4_shots": ""}

        result = parse_scorebook_entry(player_data)

        assert result["player_id"] == 123
        assert result["fouls"] == 0

        # All stats should be zero
        total = result["total_stats"]
        for key in total:
            assert total[key] == 0


class TestCalculateTeamScoreFromPlayers:
    """Tests for calculate_team_score_from_players function."""

    def test_empty_players_list(self):
        """Test calculating score with no players."""
        assert calculate_team_score_from_players([]) == 0

    def test_single_player(self):
        """Test calculating score for single player."""
        players_data = [{"qt1_shots": "22", "qt2_shots": "3", "qt3_shots": "11", "qt4_shots": ""}]

        score = calculate_team_score_from_players(players_data)
        assert score == 9  # 4 + 3 + 2

    def test_multiple_players(self):
        """Test calculating score for multiple players."""
        players_data = [
            {"qt1_shots": "22-", "qt2_shots": "3/", "qt3_shots": "", "qt4_shots": "1x"},
            {"qt1_shots": "3", "qt2_shots": "22", "qt3_shots": "1", "qt4_shots": ""},
        ]

        score = calculate_team_score_from_players(players_data)
        assert score == 16  # Player 1: 4 + 3 + 0 + 1 = 8, Player 2: 3 + 4 + 1 + 0 = 8


class TestGetShootingPercentages:
    """Tests for get_shooting_percentages function."""

    def test_all_zeros(self):
        """Test percentages when no shots attempted."""
        stats = {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}
        percentages = get_shooting_percentages(stats)

        assert percentages["ft_pct"] == 0.0
        assert percentages["fg2_pct"] == 0.0
        assert percentages["fg3_pct"] == 0.0
        assert percentages["fg_pct"] == 0.0

    def test_perfect_shooting(self):
        """Test percentages with perfect shooting."""
        stats = {"ftm": 5, "fta": 5, "fg2m": 3, "fg2a": 3, "fg3m": 2, "fg3a": 2}
        percentages = get_shooting_percentages(stats)

        assert percentages["ft_pct"] == 100.0
        assert percentages["fg2_pct"] == 100.0
        assert percentages["fg3_pct"] == 100.0
        assert percentages["fg_pct"] == 100.0

    def test_mixed_shooting(self):
        """Test percentages with mixed shooting results."""
        stats = {"ftm": 3, "fta": 4, "fg2m": 5, "fg2a": 10, "fg3m": 2, "fg3a": 6}
        percentages = get_shooting_percentages(stats)

        assert percentages["ft_pct"] == 75.0
        assert percentages["fg2_pct"] == 50.0
        assert percentages["fg3_pct"] == 33.3
        assert percentages["fg_pct"] == 43.8  # 7/16

    def test_only_free_throws(self):
        """Test percentages with only free throws."""
        stats = {"ftm": 8, "fta": 10, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}
        percentages = get_shooting_percentages(stats)

        assert percentages["ft_pct"] == 80.0
        assert percentages["fg2_pct"] == 0.0
        assert percentages["fg3_pct"] == 0.0
        assert percentages["fg_pct"] == 0.0


class TestFormatScoringNotationHelp:
    """Tests for format_scoring_notation_help function."""

    def test_help_format(self):
        """Test that help returns expected format."""
        help_text = format_scoring_notation_help()

        assert "free_throws" in help_text
        assert "two_points" in help_text
        assert "three_points" in help_text
        assert "examples" in help_text

        # Check specific notation
        assert help_text["free_throws"]["1"] == "Made free throw"
        assert help_text["free_throws"]["x"] == "Missed free throw"
        assert help_text["two_points"]["2"] == "Made 2-point shot"
        assert help_text["two_points"]["-"] == "Missed 2-point shot"
        assert help_text["three_points"]["3"] == "Made 3-point shot"
        assert help_text["three_points"]["/"] == "Missed 3-point shot"

        # Check examples exist
        assert "22-1x" in help_text["examples"]
        assert "3/2" in help_text["examples"]
