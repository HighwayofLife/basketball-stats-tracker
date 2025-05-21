"""
Test module for CSV schemas using Pydantic.
"""

import pytest
from pydantic import ValidationError

from app.schemas.csv_schemas import GameInfoSchema, GameStatsCSVInputSchema, PlayerStatsRowSchema


class TestGameInfoSchema:
    """Tests for the GameInfoSchema."""

    def test_valid_game_info(self):
        """Test validating valid game information."""
        game_info = {"PlayingTeam": "Team A", "OpponentTeam": "Team B", "Date": "2025-05-01"}
        validated = GameInfoSchema(**game_info)

        assert validated.PlayingTeam == "Team A"
        assert validated.OpponentTeam == "Team B"
        assert validated.Date == "2025-05-01"

    def test_missing_playing_team(self):
        """Test validating game info with missing playing team."""
        game_info = {"OpponentTeam": "Team B", "Date": "2025-05-01"}
        with pytest.raises(ValidationError) as excinfo:
            GameInfoSchema(**game_info)

        assert "PlayingTeam" in str(excinfo.value)
        assert "Field required" in str(excinfo.value)

    def test_missing_opponent_team(self):
        """Test validating game info with missing opponent team."""
        game_info = {"PlayingTeam": "Team A", "Date": "2025-05-01"}
        with pytest.raises(ValidationError) as excinfo:
            GameInfoSchema(**game_info)

        assert "OpponentTeam" in str(excinfo.value)
        assert "Field required" in str(excinfo.value)

    def test_missing_date(self):
        """Test validating game info with missing date."""
        game_info = {"PlayingTeam": "Team A", "OpponentTeam": "Team B"}
        with pytest.raises(ValidationError) as excinfo:
            GameInfoSchema(**game_info)

        assert "Date" in str(excinfo.value)
        assert "Field required" in str(excinfo.value)

    def test_invalid_date_format(self):
        """Test validating game info with invalid date format."""
        game_info = {
            "PlayingTeam": "Team A",
            "OpponentTeam": "Team B",
            "Date": "05/01/2025",  # Should be YYYY-MM-DD
        }
        with pytest.raises(ValidationError) as excinfo:
            GameInfoSchema(**game_info)

        assert "Date" in str(excinfo.value)
        # Accept Pydantic's default error message for pattern mismatch
        assert "string should match pattern" in str(excinfo.value).lower()


class TestPlayerStatsRowSchema:
    """Tests for the PlayerStatsRowSchema."""

    def test_valid_player_stats_row(self):
        """Test validating valid player stats row."""
        player_stats = {
            "TeamName": "Team A",
            "PlayerJersey": 10,
            "PlayerName": "Player One",
            "Fouls": 2,
            "QT1Shots": "22-1x",
            "QT2Shots": "3/2",
            "QT3Shots": "11",
            "QT4Shots": "",
        }
        validated = PlayerStatsRowSchema(**player_stats)

        assert validated.TeamName == "Team A"
        assert validated.PlayerJersey == 10
        assert validated.PlayerName == "Player One"
        assert validated.Fouls == 2
        assert validated.QT1Shots == "22-1x"
        assert validated.QT2Shots == "3/2"
        assert validated.QT3Shots == "11"
        assert validated.QT4Shots == ""

    def test_missing_team_name(self):
        """Test validating player stats row with missing team name."""
        player_stats = {
            "PlayerJersey": 10,
            "PlayerName": "Player One",
            "Fouls": 2,
            "QT1Shots": "22-1x",
            "QT2Shots": "3/2",
            "QT3Shots": "11",
            "QT4Shots": "",
        }
        with pytest.raises(ValidationError) as excinfo:
            PlayerStatsRowSchema(**player_stats)

        assert "TeamName" in str(excinfo.value)
        assert "Field required" in str(excinfo.value)

    def test_invalid_player_jersey(self):
        """Test validating player stats row with invalid player jersey."""
        player_stats = {
            "TeamName": "Team A",
            "PlayerJersey": "Ten",  # Should be an integer
            "PlayerName": "Player One",
            "Fouls": 2,
            "QT1Shots": "22-1x",
            "QT2Shots": "3/2",
            "QT3Shots": "11",
            "QT4Shots": "",
        }
        with pytest.raises(ValidationError) as excinfo:
            PlayerStatsRowSchema(**player_stats)

        assert "PlayerJersey" in str(excinfo.value)
        assert "Input should be a valid integer" in str(excinfo.value)

    def test_negative_fouls(self):
        """Test validating player stats row with negative fouls."""
        player_stats = {
            "TeamName": "Team A",
            "PlayerJersey": 10,
            "PlayerName": "Player One",
            "Fouls": -1,  # Should be non-negative
            "QT1Shots": "22-1x",
            "QT2Shots": "3/2",
            "QT3Shots": "11",
            "QT4Shots": "",
        }
        with pytest.raises(ValidationError) as excinfo:
            PlayerStatsRowSchema(**player_stats)

        assert "Fouls" in str(excinfo.value)
        assert "Input should be greater than or equal to 0" in str(excinfo.value)


class TestGameStatsCSVInputSchema:
    """Tests for the GameStatsCSVInputSchema."""

    def test_valid_game_stats_csv_input(self):
        """Test validating valid game stats CSV input."""
        # Create GameInfoSchema first
        game_info_data = {"PlayingTeam": "Team A", "OpponentTeam": "Team B", "Date": "2025-05-01"}
        game_info = GameInfoSchema(**game_info_data)

        # Create PlayerStatsRowSchema objects
        player_stats_data = [
            {
                "TeamName": "Team A",
                "PlayerJersey": 10,
                "PlayerName": "Player One",
                "Fouls": 2,
                "QT1Shots": "22-1x",
                "QT2Shots": "3/2",
                "QT3Shots": "11",
                "QT4Shots": "",
            },
            {
                "TeamName": "Team B",
                "PlayerJersey": 5,
                "PlayerName": "Player Alpha",
                "Fouls": 1,
                "QT1Shots": "x",
                "QT2Shots": "11",
                "QT3Shots": "",
                "QT4Shots": "33-",
            },
        ]
        player_stats = [PlayerStatsRowSchema(**data) for data in player_stats_data]

        # Now create the full schema with proper types
        csv_input = {
            "game_info": game_info,
            "player_stats": player_stats,
        }
        validated = GameStatsCSVInputSchema(**csv_input)

        assert validated.game_info.PlayingTeam == "Team A"
        assert validated.game_info.OpponentTeam == "Team B"
        assert validated.game_info.Date == "2025-05-01"
        assert len(validated.player_stats) == 2
        assert validated.player_stats[0].PlayerName == "Player One"
        assert validated.player_stats[1].PlayerName == "Player Alpha"

    def test_missing_game_info(self):
        """Test validating CSV input with missing game info."""
        # Create player stats row objects first
        player_data = {
            "TeamName": "Team A",
            "PlayerJersey": 10,
            "PlayerName": "Player One",
            "Fouls": 2,
            "QT1Shots": "22-1x",
            "QT2Shots": "3/2",
            "QT3Shots": "11",
            "QT4Shots": "",
        }
        player_stats = [PlayerStatsRowSchema(**player_data)]

        # Missing game_info
        csv_input = {"player_stats": player_stats}
        with pytest.raises(ValidationError) as excinfo:
            GameStatsCSVInputSchema(**csv_input)

        assert "game_info" in str(excinfo.value)
        assert "Field required" in str(excinfo.value)

    def test_empty_player_stats(self):
        """Test validating CSV input with empty player stats."""
        # Create game info first
        game_info_data = {"PlayingTeam": "Team A", "OpponentTeam": "Team B", "Date": "2025-05-01"}
        game_info = GameInfoSchema(**game_info_data)

        # Empty player stats
        csv_input = {
            "game_info": game_info,
            "player_stats": [],
        }
        with pytest.raises(ValidationError) as excinfo:
            GameStatsCSVInputSchema(**csv_input)

        assert "player_stats" in str(excinfo.value)
        assert "List should have at least 1 item" in str(excinfo.value)
