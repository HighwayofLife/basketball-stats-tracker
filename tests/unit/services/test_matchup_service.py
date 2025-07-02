"""Unit tests for the MatchupService."""

from datetime import date

from app.data_access.models import (
    Game,
    Player,
    PlayerSeasonStats,
    ScheduledGame,
    ScheduledGameStatus,
    Team,
    TeamSeasonStats,
)
from app.services.matchup_service import MatchupService


class TestMatchupService:
    """Test cases for MatchupService."""

    def test_get_matchup_data_success(self, db_session):
        """Test successful retrieval of matchup data."""
        # Create test teams
        home_team = Team(id=1, name="home_team", display_name="Home Team")
        away_team = Team(id=2, name="away_team", display_name="Away Team")
        db_session.add_all([home_team, away_team])

        # Create scheduled game
        scheduled_game = ScheduledGame(
            id=1,
            home_team_id=1,
            away_team_id=2,
            scheduled_date=date(2024, 3, 15),
            season_id=1,
            status=ScheduledGameStatus.SCHEDULED,
        )
        db_session.add(scheduled_game)

        # Create team season stats
        home_stats = TeamSeasonStats(
            team_id=1,
            season="2024-2025",
            games_played=10,
            wins=7,
            losses=3,
            total_points_for=855,
            total_points_against=782,
            total_ftm=150,
            total_fta=200,
            total_2pm=260,
            total_2pa=500,
            total_3pm=70,
            total_3pa=200,
        )
        away_stats = TeamSeasonStats(
            team_id=2,
            season="2024-2025",
            games_played=10,
            wins=5,
            losses=5,
            total_points_for=800,
            total_points_against=820,
            total_ftm=140,
            total_fta=200,
            total_2pm=240,
            total_2pa=500,
            total_3pm=66,
            total_3pa=200,
        )
        db_session.add_all([home_stats, away_stats])

        # Create players and their stats
        home_player = Player(id=1, name="Home Player", team_id=1, jersey_number="10")
        away_player = Player(id=2, name="Away Player", team_id=2, jersey_number="20")
        db_session.add_all([home_player, away_player])

        home_player_stats = PlayerSeasonStats(
            player_id=1,
            season="2024-2025",
            games_played=10,
            total_ftm=50,
            total_fta=60,
            total_2pm=80,
            total_2pa=150,
            total_3pm=25,
            total_3pa=75,
        )
        away_player_stats = PlayerSeasonStats(
            player_id=2,
            season="2024-2025",
            games_played=10,
            total_ftm=40,
            total_fta=55,
            total_2pm=70,
            total_2pa=140,
            total_3pm=20,
            total_3pa=65,
        )
        db_session.add_all([home_player_stats, away_player_stats])

        # Create historical games
        past_game = Game(
            id=1,
            date=date(2024, 2, 1),
            playing_team_id=1,
            opponent_team_id=2,
            playing_team_score=90,
            opponent_team_score=85,
        )
        db_session.add(past_game)

        db_session.commit()

        # Test the service
        service = MatchupService(db_session)
        result = service.get_matchup_data(1)

        assert result is not None
        assert result["scheduled_game"].id == 1
        assert result["home_team"]["team"].id == 1
        assert result["away_team"]["team"].id == 2
        assert result["home_team"]["season_stats"]["wins"] == 7
        assert result["away_team"]["season_stats"]["wins"] == 5
        assert len(result["home_team"]["top_players"]) == 1
        assert len(result["away_team"]["top_players"]) == 1
        assert len(result["head_to_head"]) == 1

    def test_get_matchup_data_not_found(self, db_session):
        """Test retrieval when scheduled game not found."""
        service = MatchupService(db_session)
        result = service.get_matchup_data(999)

        assert result is None

    def test_get_matchup_data_missing_teams(self, db_session):
        """Test retrieval when teams are missing."""
        # Create scheduled game without teams
        scheduled_game = ScheduledGame(
            id=1,
            home_team_id=999,
            away_team_id=998,
            scheduled_date=date(2024, 3, 15),
            season_id=1,
            status=ScheduledGameStatus.SCHEDULED,
        )
        db_session.add(scheduled_game)
        db_session.commit()

        service = MatchupService(db_session)
        result = service.get_matchup_data(1)

        assert result is None

    def test_get_team_season_stats(self, db_session):
        """Test retrieval of team season stats."""
        # Create team and stats
        team = Team(id=1, name="test_team")
        db_session.add(team)

        stats = TeamSeasonStats(
            team_id=1,
            season="2024-2025",
            games_played=10,
            wins=6,
            losses=4,
            total_points_for=800,
            total_points_against=750,
            total_ftm=100,
            total_fta=150,
            total_2pm=200,
            total_2pa=400,
            total_3pm=50,
            total_3pa=150,
        )
        db_session.add(stats)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_team_season_stats(1, "2024-2025")

        assert result is not None
        assert result["wins"] == 6
        assert result["ppg"] == 80.0

    def test_get_team_season_stats_not_found(self, db_session):
        """Test team season stats when not found."""
        service = MatchupService(db_session)
        result = service._get_team_season_stats(999, "2024-2025")

        assert result is None

    def test_get_player_season_stats(self, db_session):
        """Test retrieval of player season stats."""
        # Create team and players
        team = Team(id=1, name="test_team")
        db_session.add(team)

        players = [Player(id=i, name=f"Player {i}", team_id=1, jersey_number=str(i)) for i in range(1, 8)]
        db_session.add_all(players)

        # Create player stats with varying points
        player_stats = []
        for i in range(1, 8):
            total_points = (20 - i) * 10  # Descending total points
            player_stats.append(
                PlayerSeasonStats(
                    player_id=i,
                    season="2024-2025",
                    games_played=10,
                    total_ftm=total_points // 4,
                    total_fta=total_points // 3,
                    total_2pm=(total_points * 2) // 10,
                    total_2pa=(total_points * 4) // 10,
                    total_3pm=(total_points * 1) // 15,
                    total_3pa=(total_points * 2) // 15,
                )
            )
        db_session.add_all(player_stats)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_player_season_stats(1, "2024-2025", limit=5)

        assert len(result) == 5
        # Player 1: total_points = (20 - 1) * 10 = 190, total = 47+38+12=97, ppg = 190/10 = 19.0
        # But actual calculation: ftm + 2*2pm + 3*3pm = 47 + 2*38 + 3*12 = 47 + 76 + 36 = 159, ppg = 15.9
        assert result[0]["ppg"] == 15.9  # Player 1 has highest PPG
        assert result[4]["ppg"] == 12.7  # Player 5 has 5th highest PPG

    def test_get_player_season_stats_no_games_played(self, db_session):
        """Test player stats filtering when games_played is 0."""
        team = Team(id=1, name="test_team")
        player = Player(id=1, name="Benched Player", team_id=1, jersey_number="99")
        db_session.add_all([team, player])

        # Player with 0 games played
        stats = PlayerSeasonStats(
            player_id=1,
            season="2024-2025",
            games_played=0,
            total_ftm=0,
            total_fta=0,
            total_2pm=0,
            total_2pa=0,
            total_3pm=0,
            total_3pa=0,
        )
        db_session.add(stats)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_player_season_stats(1, "2024-2025")

        assert len(result) == 0  # Should filter out players with 0 games

    def test_get_head_to_head_history(self, db_session):
        """Test retrieval of head-to-head history."""
        # Create teams
        team1 = Team(id=1, name="team1")
        team2 = Team(id=2, name="team2")
        db_session.add_all([team1, team2])

        # Create games between teams
        games = [
            Game(
                id=1,
                date=date(2024, 1, 1),
                playing_team_id=1,
                opponent_team_id=2,
                playing_team_score=85,
                opponent_team_score=80,
            ),
            Game(
                id=2,
                date=date(2024, 1, 15),
                playing_team_id=2,
                opponent_team_id=1,
                playing_team_score=90,
                opponent_team_score=88,
            ),
            Game(
                id=3,
                date=date(2024, 2, 1),
                playing_team_id=1,
                opponent_team_id=2,
                playing_team_score=92,
                opponent_team_score=87,
            ),
        ]
        db_session.add_all(games)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_head_to_head_history(1, 2, limit=5)

        assert len(result) == 3
        assert result[0].id == 3  # Most recent game first
        assert result[2].id == 1  # Oldest game last

    def test_get_head_to_head_history_no_games(self, db_session):
        """Test head-to-head when no games exist."""
        service = MatchupService(db_session)
        result = service._get_head_to_head_history(1, 2)

        assert len(result) == 0

    def test_get_head_to_head_history_limit(self, db_session):
        """Test head-to-head history respects limit."""
        # Create teams
        team1 = Team(id=1, name="team1")
        team2 = Team(id=2, name="team2")
        db_session.add_all([team1, team2])

        # Create 10 games
        for i in range(10):
            game = Game(
                id=i + 1,
                date=date(2024, 1, i + 1),
                playing_team_id=1 if i % 2 == 0 else 2,
                opponent_team_id=2 if i % 2 == 0 else 1,
                playing_team_score=80 + i,
                opponent_team_score=75 + i,
            )
            db_session.add(game)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_head_to_head_history(1, 2, limit=3)

        assert len(result) == 3
