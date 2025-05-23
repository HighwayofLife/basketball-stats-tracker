"""
Test module for input_parser.py
"""

from app.utils.input_parser import parse_quarter_shot_string


class TestParseQuarterShotString:
    """Tests for the parse_quarter_shot_string function."""

    def test_empty_shot_string(self, test_shot_mapping):
        """Tests parsing an empty shot string."""
        result = parse_quarter_shot_string("", test_shot_mapping)

        # Empty string should result in all zeros
        assert result == {"ftm": 0, "fta": 0, "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0}

    def test_free_throws_only(self, test_shot_mapping):
        """Tests parsing a shot string with only free throws."""
        result = parse_quarter_shot_string("11xxx", test_shot_mapping)

        # Should have 2 made FTs out of 5 attempts, no field goals
        assert result["ftm"] == 2
        assert result["fta"] == 5
        assert result["fg2m"] == 0
        assert result["fg2a"] == 0
        assert result["fg3m"] == 0
        assert result["fg3a"] == 0

    def test_two_pointers_only(self, test_shot_mapping):
        """Tests parsing a shot string with only 2-point shots."""
        result = parse_quarter_shot_string("22-2-", test_shot_mapping)

        # Should have 3 made 2P field goals out of 5 attempts, no others
        assert result["ftm"] == 0
        assert result["fta"] == 0
        assert result["fg2m"] == 3
        assert result["fg2a"] == 5
        assert result["fg3m"] == 0
        assert result["fg3a"] == 0

    def test_three_pointers_only(self, test_shot_mapping):
        """Tests parsing a shot string with only 3-point shots."""
        result = parse_quarter_shot_string("33//", test_shot_mapping)

        # Should have 2 made 3P field goals out of 4 attempts, no others
        assert result["ftm"] == 0
        assert result["fta"] == 0
        assert result["fg2m"] == 0
        assert result["fg2a"] == 0
        assert result["fg3m"] == 2
        assert result["fg3a"] == 4

    def test_mixed_shot_types(self, test_shot_mapping):
        """Tests parsing a shot string with mixed shot types."""
        result = parse_quarter_shot_string("22-1x3/", test_shot_mapping)

        # Should have:
        # - 1 made FT out of 2 attempts
        # - 2 made 2P out of 3 attempts
        # - 1 made 3P out of 2 attempts
        assert result["ftm"] == 1
        assert result["fta"] == 2
        assert result["fg2m"] == 2
        assert result["fg2a"] == 3
        assert result["fg3m"] == 1
        assert result["fg3a"] == 2

    def test_unknown_characters(self, test_shot_mapping):
        """Tests that unknown characters in the shot string are ignored."""
        result = parse_quarter_shot_string("22?!A#", test_shot_mapping)

        # Should have:
        # - 2 made 2P out of 2 attempts
        # - Unknown characters are ignored
        assert result["ftm"] == 0
        assert result["fta"] == 0
        assert result["fg2m"] == 2
        assert result["fg2a"] == 2
        assert result["fg3m"] == 0
        assert result["fg3a"] == 0
