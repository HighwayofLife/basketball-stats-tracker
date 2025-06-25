# tests/unit/web_ui/test_schemas.py

"""Unit tests for web UI schemas."""

import pytest
from pydantic import ValidationError

from app.web_ui.schemas import BoxScoreResponse, GameSummary, PlayerStats, TeamStats


class TestGameSummary:
    """Tests for GameSummary schema."""

    def test_valid_game_summary(self):
        """Test creating a valid GameSummary."""
        data = {
            "id": 1,
            "date": "2024-01-15",
            "home_team": "Lakers",
            "home_team_id": 1,
            "away_team": "Warriors",
            "away_team_id": 2,
            "home_score": 110,
            "away_score": 105,
        }
        game_summary = GameSummary(**data)
        assert game_summary.id == 1
        assert game_summary.date == "2024-01-15"
        assert game_summary.home_team == "Lakers"
        assert game_summary.home_team_id == 1
        assert game_summary.away_team == "Warriors"
        assert game_summary.away_team_id == 2
        assert game_summary.home_score == 110
        assert game_summary.away_score == 105

    def test_game_summary_missing_required_field(self):
        """Test GameSummary with missing required field."""
        data = {
            "id": 1,
            "date": "2024-01-15",
            "home_team": "Lakers",
            "home_team_id": 1,
            "away_team": "Warriors",
            # Missing away_team_id
            "home_score": 110,
            "away_score": 105,
        }
        with pytest.raises(ValidationError) as exc_info:
            GameSummary(**data)
        assert "away_team_id" in str(exc_info.value)

    def test_game_summary_invalid_type(self):
        """Test GameSummary with invalid field type."""
        data = {
            "id": "not_an_int",  # Should be int
            "date": "2024-01-15",
            "home_team": "Lakers",
            "home_team_id": 1,
            "away_team": "Warriors",
            "away_team_id": 2,
            "home_score": 110,
            "away_score": 105,
        }
        with pytest.raises(ValidationError) as exc_info:
            GameSummary(**data)
        assert "id" in str(exc_info.value)

    def test_game_summary_model_dump(self):
        """Test GameSummary model_dump method."""
        data = {
            "id": 1,
            "date": "2024-01-15",
            "home_team": "Lakers",
            "home_team_id": 1,
            "home_team_record": None,
            "away_team": "Warriors",
            "away_team_id": 2,
            "away_team_record": None,
            "home_score": 110,
            "away_score": 105,
        }
        game_summary = GameSummary(**data)
        dumped = game_summary.model_dump()
        assert dumped == data


class TestPlayerStats:
    """Tests for PlayerStats schema."""

    def test_valid_player_stats(self):
        """Test creating valid PlayerStats."""
        data = {
            "player_id": 1,
            "name": "LeBron James",
            "stats": {
                "points": 25,
                "rebounds": 8,
                "assists": 7,
                "field_goals_made": 10,
                "field_goals_attempted": 20,
            },
        }
        player_stats = PlayerStats(**data)
        assert player_stats.player_id == 1
        assert player_stats.name == "LeBron James"
        assert player_stats.stats["points"] == 25
        assert player_stats.stats["rebounds"] == 8

    def test_player_stats_empty_stats_dict(self):
        """Test PlayerStats with empty stats dictionary."""
        data = {"player_id": 1, "name": "LeBron James", "stats": {}}
        player_stats = PlayerStats(**data)
        assert player_stats.player_id == 1
        assert player_stats.name == "LeBron James"
        assert player_stats.stats == {}

    def test_player_stats_missing_field(self):
        """Test PlayerStats with missing required field."""
        data = {
            "player_id": 1,
            # Missing name
            "stats": {"points": 25},
        }
        with pytest.raises(ValidationError) as exc_info:
            PlayerStats(**data)
        assert "name" in str(exc_info.value)

    def test_player_stats_various_stat_types(self):
        """Test PlayerStats with various stat value types."""
        data = {
            "player_id": 1,
            "name": "Player One",
            "stats": {
                "points": 25,
                "shooting_percentage": 0.456,
                "is_starter": True,
                "position": "PG",
                "minutes": "32:45",
                "fouls": None,
            },
        }
        player_stats = PlayerStats(**data)
        assert player_stats.stats["points"] == 25
        assert player_stats.stats["shooting_percentage"] == 0.456
        assert player_stats.stats["is_starter"] is True
        assert player_stats.stats["position"] == "PG"
        assert player_stats.stats["minutes"] == "32:45"
        assert player_stats.stats["fouls"] is None


class TestTeamStats:
    """Tests for TeamStats schema."""

    def test_valid_team_stats(self):
        """Test creating valid TeamStats."""
        data = {
            "team_id": 1,
            "name": "Lakers",
            "score": 110,
            "stats": {
                "field_goals_made": 40,
                "field_goals_attempted": 85,
                "three_pointers_made": 12,
                "rebounds": 45,
                "assists": 25,
            },
            "players": [
                {
                    "player_id": 1,
                    "name": "LeBron James",
                    "stats": {"points": 25, "rebounds": 8, "assists": 7},
                },
                {
                    "player_id": 2,
                    "name": "Anthony Davis",
                    "stats": {"points": 28, "rebounds": 12, "assists": 3},
                },
            ],
        }
        team_stats = TeamStats(**data)
        assert team_stats.team_id == 1
        assert team_stats.name == "Lakers"
        assert team_stats.score == 110
        assert team_stats.stats["field_goals_made"] == 40
        assert len(team_stats.players) == 2
        assert team_stats.players[0].name == "LeBron James"
        assert team_stats.players[1].name == "Anthony Davis"

    def test_team_stats_empty_players_list(self):
        """Test TeamStats with empty players list."""
        data = {
            "team_id": 1,
            "name": "Lakers",
            "score": 110,
            "stats": {"rebounds": 45},
            "players": [],
        }
        team_stats = TeamStats(**data)
        assert team_stats.team_id == 1
        assert team_stats.name == "Lakers"
        assert team_stats.score == 110
        assert team_stats.players == []

    def test_team_stats_invalid_player(self):
        """Test TeamStats with invalid player data."""
        data = {
            "team_id": 1,
            "name": "Lakers",
            "score": 110,
            "stats": {},
            "players": [
                {
                    "player_id": 1,
                    # Missing name
                    "stats": {"points": 25},
                }
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            TeamStats(**data)
        assert "name" in str(exc_info.value)

    def test_team_stats_missing_field(self):
        """Test TeamStats with missing required field."""
        data = {
            "team_id": 1,
            "name": "Lakers",
            # Missing score
            "stats": {},
            "players": [],
        }
        with pytest.raises(ValidationError) as exc_info:
            TeamStats(**data)
        assert "score" in str(exc_info.value)

    def test_team_stats_with_top_players(self):
        """Test TeamStats with top_players field for Game Leaders section."""
        top_players_data = [
            {
                "player_id": 1,
                "name": "LeBron James",
                "jersey": "6",
                "points": 25,
                "fg_percentage": 48.5,
                "fg2m": 8,
                "fg2a": 15,
                "fg3m": 3,
                "fg3a": 7,
            },
            {
                "player_id": 2,
                "name": "Anthony Davis",
                "jersey": "3",
                "points": 22,
                "fg_percentage": 52.0,
                "fg2m": 9,
                "fg2a": 16,
                "fg3m": 1,
                "fg3a": 3,
            },
        ]

        data = {
            "team_id": 1,
            "name": "Lakers",
            "score": 110,
            "stats": {"rebounds": 45},
            "players": [],
            "top_players": top_players_data,
        }

        team_stats = TeamStats(**data)
        assert team_stats.team_id == 1
        assert team_stats.name == "Lakers"
        assert len(team_stats.top_players) == 2
        assert team_stats.top_players[0]["name"] == "LeBron James"
        assert team_stats.top_players[0]["points"] == 25
        assert team_stats.top_players[1]["name"] == "Anthony Davis"
        assert team_stats.top_players[1]["points"] == 22

    def test_team_stats_empty_top_players(self):
        """Test TeamStats with empty top_players list."""
        data = {
            "team_id": 1,
            "name": "Lakers",
            "score": 110,
            "stats": {"rebounds": 45},
            "players": [],
            "top_players": [],
        }

        team_stats = TeamStats(**data)
        assert team_stats.team_id == 1
        assert team_stats.top_players == []


class TestBoxScoreResponse:
    """Tests for BoxScoreResponse schema."""

    def test_valid_box_score_response(self):
        """Test creating valid BoxScoreResponse."""
        data = {
            "game_id": 1,
            "game_date": "2024-01-15",
            "home_team": {
                "team_id": 1,
                "name": "Lakers",
                "score": 110,
                "stats": {"rebounds": 45, "assists": 25},
                "players": [
                    {
                        "player_id": 1,
                        "name": "LeBron James",
                        "stats": {"points": 25, "rebounds": 8},
                    }
                ],
            },
            "away_team": {
                "team_id": 2,
                "name": "Warriors",
                "score": 105,
                "stats": {"rebounds": 42, "assists": 23},
                "players": [
                    {
                        "player_id": 3,
                        "name": "Stephen Curry",
                        "stats": {"points": 30, "assists": 6},
                    }
                ],
            },
        }
        box_score = BoxScoreResponse(**data)
        assert box_score.game_id == 1
        assert box_score.game_date == "2024-01-15"
        assert box_score.home_team.name == "Lakers"
        assert box_score.home_team.score == 110
        assert box_score.away_team.name == "Warriors"
        assert box_score.away_team.score == 105
        assert len(box_score.home_team.players) == 1
        assert len(box_score.away_team.players) == 1

    def test_box_score_response_missing_field(self):
        """Test BoxScoreResponse with missing required field."""
        data = {
            "game_id": 1,
            # Missing game_date
            "home_team": {
                "team_id": 1,
                "name": "Lakers",
                "score": 110,
                "stats": {},
                "players": [],
            },
            "away_team": {
                "team_id": 2,
                "name": "Warriors",
                "score": 105,
                "stats": {},
                "players": [],
            },
        }
        with pytest.raises(ValidationError) as exc_info:
            BoxScoreResponse(**data)
        assert "game_date" in str(exc_info.value)

    def test_box_score_response_invalid_team(self):
        """Test BoxScoreResponse with invalid team data."""
        data = {
            "game_id": 1,
            "game_date": "2024-01-15",
            "home_team": {
                "team_id": 1,
                "name": "Lakers",
                # Missing score
                "stats": {},
                "players": [],
            },
            "away_team": {
                "team_id": 2,
                "name": "Warriors",
                "score": 105,
                "stats": {},
                "players": [],
            },
        }
        with pytest.raises(ValidationError) as exc_info:
            BoxScoreResponse(**data)
        assert "score" in str(exc_info.value)

    def test_box_score_response_model_dump(self):
        """Test BoxScoreResponse model_dump method."""
        data = {
            "game_id": 1,
            "game_date": "2024-01-15",
            "home_team": {
                "team_id": 1,
                "name": "Lakers",
                "score": 110,
                "stats": {"rebounds": 45},
                "players": [],
            },
            "away_team": {
                "team_id": 2,
                "name": "Warriors",
                "score": 105,
                "stats": {"rebounds": 42},
                "players": [],
            },
        }
        box_score = BoxScoreResponse(**data)
        dumped = box_score.model_dump()
        assert dumped["game_id"] == 1
        assert dumped["game_date"] == "2024-01-15"
        assert dumped["home_team"]["name"] == "Lakers"
        assert dumped["away_team"]["name"] == "Warriors"

    def test_box_score_response_complex_scenario(self):
        """Test BoxScoreResponse with complex real-world scenario."""
        data = {
            "game_id": 100,
            "game_date": "2024-01-15",
            "home_team": {
                "team_id": 1,
                "name": "Los Angeles Lakers",
                "score": 112,
                "stats": {
                    "field_goals_made": 42,
                    "field_goals_attempted": 89,
                    "field_goal_percentage": 0.472,
                    "three_pointers_made": 14,
                    "three_pointers_attempted": 35,
                    "three_point_percentage": 0.400,
                    "free_throws_made": 14,
                    "free_throws_attempted": 18,
                    "free_throw_percentage": 0.778,
                    "rebounds": 48,
                    "assists": 27,
                    "steals": 8,
                    "blocks": 5,
                    "turnovers": 12,
                },
                "players": [
                    {
                        "player_id": 1,
                        "name": "LeBron James",
                        "stats": {
                            "minutes": "35:42",
                            "points": 27,
                            "rebounds": 8,
                            "assists": 9,
                            "steals": 2,
                            "blocks": 1,
                            "turnovers": 3,
                            "fouls": 2,
                            "plus_minus": 12,
                        },
                    },
                    {
                        "player_id": 2,
                        "name": "Anthony Davis",
                        "stats": {
                            "minutes": "32:15",
                            "points": 31,
                            "rebounds": 14,
                            "assists": 3,
                            "steals": 1,
                            "blocks": 3,
                            "turnovers": 2,
                            "fouls": 3,
                            "plus_minus": 8,
                        },
                    },
                ],
            },
            "away_team": {
                "team_id": 2,
                "name": "Golden State Warriors",
                "score": 108,
                "stats": {
                    "field_goals_made": 39,
                    "field_goals_attempted": 91,
                    "field_goal_percentage": 0.429,
                    "three_pointers_made": 16,
                    "three_pointers_attempted": 41,
                    "three_point_percentage": 0.390,
                    "free_throws_made": 14,
                    "free_throws_attempted": 16,
                    "free_throw_percentage": 0.875,
                    "rebounds": 45,
                    "assists": 24,
                    "steals": 6,
                    "blocks": 3,
                    "turnovers": 15,
                },
                "players": [
                    {
                        "player_id": 3,
                        "name": "Stephen Curry",
                        "stats": {
                            "minutes": "36:20",
                            "points": 34,
                            "rebounds": 5,
                            "assists": 7,
                            "steals": 1,
                            "blocks": 0,
                            "turnovers": 4,
                            "fouls": 3,
                            "plus_minus": -5,
                        },
                    },
                ],
            },
        }
        box_score = BoxScoreResponse(**data)
        assert box_score.game_id == 100
        assert box_score.home_team.score == 112
        assert box_score.away_team.score == 108
        assert box_score.home_team.stats["field_goal_percentage"] == 0.472
        assert box_score.away_team.stats["three_point_percentage"] == 0.390
        assert box_score.home_team.players[0].stats["minutes"] == "35:42"
        assert box_score.away_team.players[0].stats["points"] == 34
