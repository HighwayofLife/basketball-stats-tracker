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
            season_id=1,
            games_played=10,
            wins=7,
            losses=3,
            ppg=85.5,
            opp_ppg=78.2,
            win_percentage=0.7,
            ft_percentage=0.75,
            fg2_percentage=0.52,
            fg3_percentage=0.35,
        )
        away_stats = TeamSeasonStats(
            team_id=2,
            season_id=1,
            games_played=10,
            wins=5,
            losses=5,
            ppg=80.0,
            opp_ppg=82.0,
            win_percentage=0.5,
            ft_percentage=0.70,
            fg2_percentage=0.48,
            fg3_percentage=0.33,
        )
        db_session.add_all([home_stats, away_stats])

        # Create players and their stats
        home_player = Player(id=1, name="Home Player", team_id=1, jersey_number="10")
        away_player = Player(id=2, name="Away Player", team_id=2, jersey_number="20")
        db_session.add_all([home_player, away_player])

        home_player_stats = PlayerSeasonStats(
            player_id=1,
            team_id=1,
            season_id=1,
            games_played=10,
            points_per_game=20.5,
            ftm=50,
            fta=60,
            fg2m=80,
            fg2a=150,
            fg3m=25,
            fg3a=75,
            ft_percentage=0.833,
        )
        away_player_stats = PlayerSeasonStats(
            player_id=2,
            team_id=2,
            season_id=1,
            games_played=10,
            points_per_game=18.0,
            ftm=40,
            fta=55,
            fg2m=70,
            fg2a=140,
            fg3m=20,
            fg3a=65,
            ft_percentage=0.727,
        )
        db_session.add_all([home_player_stats, away_player_stats])

        # Create historical games
        past_game = Game(
            id=1,
            game_date=date(2024, 2, 1),
            home_team_id=1,
            away_team_id=2,
            home_score=90,
            away_score=85,
            status="completed",
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
        assert result["home_team"]["season_stats"].wins == 7
        assert result["away_team"]["season_stats"].wins == 5
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
            team_id=1, season_id=1, games_played=10, wins=6, losses=4, ppg=80.0, opp_ppg=75.0, win_percentage=0.6
        )
        db_session.add(stats)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_team_season_stats(1, 1)

        assert result is not None
        assert result.wins == 6
        assert result.ppg == 80.0

    def test_get_team_season_stats_not_found(self, db_session):
        """Test team season stats when not found."""
        service = MatchupService(db_session)
        result = service._get_team_season_stats(999, 1)

        assert result is None

    def test_get_player_season_stats(self, db_session):
        """Test retrieval of player season stats."""
        # Create team and players
        team = Team(id=1, name="test_team")
        db_session.add(team)

        players = [Player(id=i, name=f"Player {i}", team_id=1, jersey_number=str(i)) for i in range(1, 8)]
        db_session.add_all(players)

        # Create player stats with varying PPG
        player_stats = [
            PlayerSeasonStats(
                player_id=i,
                team_id=1,
                season_id=1,
                games_played=10,
                points_per_game=20.0 - i,  # Descending PPG
            )
            for i in range(1, 8)
        ]
        db_session.add_all(player_stats)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_player_season_stats(1, 1, limit=5)

        assert len(result) == 5
        assert result[0].points_per_game == 19.0  # Player 1 has highest PPG
        assert result[4].points_per_game == 15.0  # Player 5 has 5th highest PPG

    def test_get_player_season_stats_no_games_played(self, db_session):
        """Test player stats filtering when games_played is 0."""
        team = Team(id=1, name="test_team")
        player = Player(id=1, name="Benched Player", team_id=1, jersey_number="99")
        db_session.add_all([team, player])

        # Player with 0 games played
        stats = PlayerSeasonStats(player_id=1, team_id=1, season_id=1, games_played=0, points_per_game=0.0)
        db_session.add(stats)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_player_season_stats(1, 1)

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
                game_date=date(2024, 1, 1),
                home_team_id=1,
                away_team_id=2,
                home_score=85,
                away_score=80,
                status="completed",
            ),
            Game(
                id=2,
                game_date=date(2024, 1, 15),
                home_team_id=2,
                away_team_id=1,
                home_score=90,
                away_score=88,
                status="completed",
            ),
            Game(
                id=3,
                game_date=date(2024, 2, 1),
                home_team_id=1,
                away_team_id=2,
                home_score=92,
                away_score=87,
                status="completed",
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
                game_date=date(2024, 1, i + 1),
                home_team_id=1 if i % 2 == 0 else 2,
                away_team_id=2 if i % 2 == 0 else 1,
                home_score=80 + i,
                away_score=75 + i,
                status="completed",
            )
            db_session.add(game)
        db_session.commit()

        service = MatchupService(db_session)
        result = service._get_head_to_head_history(1, 2, limit=3)

        assert len(result) == 3
