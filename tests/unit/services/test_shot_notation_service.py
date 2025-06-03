"""Tests for ShotNotationService."""

from datetime import date

from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team
from app.services.shot_notation_service import ShotNotationService


class TestShotNotationService:
    """Test cases for ShotNotationService."""

    def test_stats_to_notation_basic(self):
        """Test basic conversion of stats to notation."""
        # Test with simple stats
        notation = ShotNotationService.stats_to_notation(ftm=2, fta=3, fg2m=3, fg2a=5, fg3m=1, fg3a=2)
        assert notation == "222--3/11x"

    def test_stats_to_notation_no_misses(self):
        """Test conversion when all shots are made."""
        notation = ShotNotationService.stats_to_notation(ftm=2, fta=2, fg2m=3, fg2a=3, fg3m=1, fg3a=1)
        assert notation == "222311"

    def test_stats_to_notation_all_misses(self):
        """Test conversion when all shots are missed."""
        notation = ShotNotationService.stats_to_notation(ftm=0, fta=2, fg2m=0, fg2a=3, fg3m=0, fg3a=1)
        assert notation == "---/xx"

    def test_stats_to_notation_empty(self):
        """Test conversion with no shots."""
        notation = ShotNotationService.stats_to_notation(ftm=0, fta=0, fg2m=0, fg2a=0, fg3m=0, fg3a=0)
        assert notation == ""

    def test_player_game_stats_to_scorebook_format_with_quarters(self):
        """Test converting PlayerGameStats with quarter data to scorebook format."""
        # Create test data
        team = Team(id=1, name="Home Team")
        player = Player(id=1, name="John Doe", jersey_number="23", team_id=1, team=team)
        game = Game(id=1, date=date(2025, 1, 15), playing_team_id=1, opponent_team_id=2)

        pgs = PlayerGameStats(player_id=1, game_id=1, player=player, game=game, fouls=3)

        quarter_stats = [
            PlayerQuarterStats(player_game_stat_id=1, quarter_number=1, ftm=1, fta=2, fg2m=2, fg2a=3, fg3m=0, fg3a=1),
            PlayerQuarterStats(player_game_stat_id=1, quarter_number=2, ftm=0, fta=0, fg2m=1, fg2a=2, fg3m=1, fg3a=1),
            PlayerQuarterStats(player_game_stat_id=1, quarter_number=3, ftm=2, fta=2, fg2m=0, fg2a=1, fg3m=0, fg3a=0),
            PlayerQuarterStats(player_game_stat_id=1, quarter_number=4, ftm=0, fta=1, fg2m=1, fg2a=1, fg3m=0, fg3a=0),
        ]

        result = ShotNotationService.player_game_stats_to_scorebook_format(pgs, quarter_stats)

        assert result["player_id"] == 1
        assert result["player_name"] == "John Doe"
        assert result["jersey_number"] == "23"
        assert result["team"] == "home"
        assert result["fouls"] == 3
        assert result["shots_q1"] == "22-/1x"
        assert result["shots_q2"] == "2-3"
        assert result["shots_q3"] == "-11"
        assert result["shots_q4"] == "2x"

    def test_player_game_stats_to_scorebook_format_no_quarters(self):
        """Test converting PlayerGameStats without quarter data to scorebook format."""
        # Create test data
        team = Team(id=2, name="Away Team")
        player = Player(id=2, name="Jane Smith", jersey_number="10", team_id=2, team=team)
        game = Game(id=1, date=date(2025, 1, 15), playing_team_id=1, opponent_team_id=2)

        pgs = PlayerGameStats(
            player_id=2,
            game_id=1,
            player=player,
            game=game,
            total_ftm=5,
            total_fta=6,
            total_2pm=4,
            total_2pa=8,
            total_3pm=2,
            total_3pa=5,
            fouls=2,
        )

        result = ShotNotationService.player_game_stats_to_scorebook_format(pgs)

        assert result["player_id"] == 2
        assert result["player_name"] == "Jane Smith"
        assert result["jersey_number"] == "10"
        assert result["team"] == "away"
        assert result["fouls"] == 2
        assert result["shots_q1"] == "2222----33///11111x"
        assert result["shots_q2"] == ""
        assert result["shots_q3"] == ""
        assert result["shots_q4"] == ""

    def test_game_to_scorebook_format(self):
        """Test converting a complete game to scorebook format."""
        # Create test data
        game = Game(
            id=1,
            date=date(2025, 1, 15),
            playing_team_id=1,
            opponent_team_id=2,
            location="Main Court",
            notes="Championship game",
        )

        home_team = Team(id=1, name="Home Team")
        away_team = Team(id=2, name="Away Team")

        player1 = Player(id=1, name="Player 1", jersey_number="1", team_id=1, team=home_team)
        player2 = Player(id=2, name="Player 2", jersey_number="2", team_id=2, team=away_team)

        player_game_stats = [
            PlayerGameStats(
                player_id=1,
                game_id=1,
                player=player1,
                game=game,
                total_ftm=2,
                total_fta=2,
                total_2pm=3,
                total_2pa=4,
                total_3pm=1,
                total_3pa=2,
                fouls=1,
            ),
            PlayerGameStats(
                player_id=2,
                game_id=1,
                player=player2,
                game=game,
                total_ftm=1,
                total_fta=3,
                total_2pm=2,
                total_2pa=3,
                total_3pm=0,
                total_3pa=1,
                fouls=3,
            ),
        ]

        player_quarter_stats = {
            1: [
                PlayerQuarterStats(
                    player_game_stat_id=1, quarter_number=1, ftm=2, fta=2, fg2m=3, fg2a=4, fg3m=1, fg3a=2
                )
            ],
            2: [],  # No quarter stats for player 2
        }

        result = ShotNotationService.game_to_scorebook_format(game, player_game_stats, player_quarter_stats)

        assert result["game_info"]["id"] == 1
        assert result["game_info"]["date"] == "2025-01-15"
        assert result["game_info"]["home_team_id"] == 1  # playing_team_id maps to home_team_id
        assert result["game_info"]["away_team_id"] == 2  # opponent_team_id maps to away_team_id
        assert result["game_info"]["location"] == "Main Court"
        assert result["game_info"]["notes"] == "Championship game"

        assert len(result["player_stats"]) == 2

        # Check player 1 (has quarter stats)
        p1_stats = result["player_stats"][0]
        assert p1_stats["player_id"] == 1
        assert p1_stats["team"] == "home"
        assert p1_stats["shots_q1"] == "222-3/11"

        # Check player 2 (no quarter stats, should have aggregated stats in Q1)
        p2_stats = result["player_stats"][1]
        assert p2_stats["player_id"] == 2
        assert p2_stats["team"] == "away"
        assert p2_stats["shots_q1"] == "22-/1xx"
