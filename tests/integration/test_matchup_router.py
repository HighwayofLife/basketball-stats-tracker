"""Integration tests for the matchup router."""

from datetime import date, time

from fastapi.testclient import TestClient

from app.data_access.models import (
    Game,
    Player,
    PlayerSeasonStats,
    ScheduledGame,
    ScheduledGameStatus,
    Season,
    Team,
    TeamSeasonStats,
)


class TestMatchupRouter:
    """Test cases for the matchup router endpoints."""

    def test_view_matchup_success(self, client: TestClient, db_session):
        """Test successful matchup view."""
        # Create test data
        season = Season(id=1, name="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
        home_team = Team(id=1, name="home_team", display_name="Home Team")
        away_team = Team(id=2, name="away_team", display_name="Away Team")
        db_session.add_all([season, home_team, away_team])

        # Create scheduled game
        scheduled_game = ScheduledGame(
            id=1,
            home_team_id=1,
            away_team_id=2,
            scheduled_date=date(2024, 3, 15),
            scheduled_time=time(19, 0),
            season_id=1,
            location="Home Arena",
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
        home_player = Player(id=1, name="Home Star", team_id=1, jersey_number="10", position="PG")
        away_player = Player(id=2, name="Away Star", team_id=2, jersey_number="20", position="SG")
        db_session.add_all([home_player, away_player])

        home_player_stats = PlayerSeasonStats(
            player_id=1,
            player=home_player,
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
            player=away_player,
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

        # Create historical game
        past_game = Game(
            id=1,
            game_date=date(2024, 2, 1),
            home_team_id=1,
            home_team=home_team,
            away_team_id=2,
            away_team=away_team,
            home_score=90,
            away_score=85,
            status="completed",
        )
        db_session.add(past_game)

        db_session.commit()

        # Test the endpoint
        response = client.get("/scheduled-games/1/matchup")

        assert response.status_code == 200
        assert "Home Team" in response.text
        assert "Away Team" in response.text
        assert "7-3" in response.text  # Home team record
        assert "5-5" in response.text  # Away team record
        assert "Team Comparison" in response.text
        assert "Top Players" in response.text
        assert "Head-to-Head History" in response.text
        assert "Home Star" in response.text
        assert "Away Star" in response.text
        assert "March 15, 2024" in response.text
        assert "07:00 PM" in response.text
        assert "Home Arena" in response.text

    def test_view_matchup_not_found(self, client: TestClient, db_session):
        """Test matchup view when scheduled game not found."""
        response = client.get("/scheduled-games/999/matchup")

        assert response.status_code == 404
        assert response.json()["detail"] == "Scheduled game not found"

    def test_view_matchup_no_stats(self, client: TestClient, db_session):
        """Test matchup view when no stats are available."""
        # Create minimal data
        season = Season(id=1, name="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
        home_team = Team(id=1, name="home_team", display_name="Home Team")
        away_team = Team(id=2, name="away_team", display_name="Away Team")
        db_session.add_all([season, home_team, away_team])

        scheduled_game = ScheduledGame(
            id=1,
            home_team_id=1,
            away_team_id=2,
            scheduled_date=date(2024, 3, 15),
            season_id=1,
            status=ScheduledGameStatus.SCHEDULED,
        )
        db_session.add(scheduled_game)
        db_session.commit()

        response = client.get("/scheduled-games/1/matchup")

        assert response.status_code == 200
        assert "Home Team" in response.text
        assert "Away Team" in response.text
        assert "0-0" in response.text  # Default record
        assert "No previous matchups" in response.text

    def test_view_matchup_no_head_to_head(self, client: TestClient, db_session):
        """Test matchup view when no head-to-head history exists."""
        # Create test data without historical games
        season = Season(id=1, name="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
        home_team = Team(id=1, name="home_team", display_name="Home Team")
        away_team = Team(id=2, name="away_team", display_name="Away Team")
        db_session.add_all([season, home_team, away_team])

        scheduled_game = ScheduledGame(
            id=1,
            home_team_id=1,
            away_team_id=2,
            scheduled_date=date(2024, 3, 15),
            season_id=1,
            status=ScheduledGameStatus.SCHEDULED,
        )
        db_session.add(scheduled_game)

        # Add some team stats
        home_stats = TeamSeasonStats(
            team_id=1, season_id=1, games_played=5, wins=3, losses=2, ppg=75.0, opp_ppg=70.0, win_percentage=0.6
        )
        db_session.add(home_stats)
        db_session.commit()

        response = client.get("/scheduled-games/1/matchup")

        assert response.status_code == 200
        assert "No previous matchups between these teams" in response.text

    def test_view_matchup_multiple_players(self, client: TestClient, db_session):
        """Test matchup view with multiple top players."""
        # Create test data
        season = Season(id=1, name="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
        home_team = Team(id=1, name="home_team", display_name="Home Team")
        db_session.add_all([season, home_team])

        # Create multiple players for home team
        players = []
        for i in range(1, 6):
            player = Player(
                id=i,
                name=f"Player {i}",
                team_id=1,
                jersey_number=str(i * 10),
                position=["PG", "SG", "SF", "PF", "C"][i - 1],
            )
            players.append(player)

            stats = PlayerSeasonStats(
                player_id=i,
                player=player,
                team_id=1,
                season_id=1,
                games_played=10,
                points_per_game=20.0 - i,  # Descending PPG
                ftm=10 * i,
                fta=12 * i,
                fg2m=20 * i,
                fg2a=40 * i,
                fg3m=5 * i,
                fg3a=15 * i,
            )
            db_session.add(stats)

        db_session.add_all(players)

        # Create away team with no players
        away_team = Team(id=2, name="away_team", display_name="Away Team")
        db_session.add(away_team)

        scheduled_game = ScheduledGame(
            id=1,
            home_team_id=1,
            away_team_id=2,
            scheduled_date=date(2024, 3, 15),
            season_id=1,
            status=ScheduledGameStatus.SCHEDULED,
        )
        db_session.add(scheduled_game)
        db_session.commit()

        response = client.get("/scheduled-games/1/matchup")

        assert response.status_code == 200
        # Check that all 5 players are shown
        for i in range(1, 6):
            assert f"Player {i}" in response.text

    def test_view_matchup_formatting(self, client: TestClient, db_session):
        """Test proper formatting of stats in matchup view."""
        # Create test data with specific values to test formatting
        season = Season(id=1, name="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
        home_team = Team(id=1, name="home_team", display_name="Home Team")
        away_team = Team(id=2, name="away_team", display_name="Away Team")
        db_session.add_all([season, home_team, away_team])

        scheduled_game = ScheduledGame(
            id=1,
            home_team_id=1,
            away_team_id=2,
            scheduled_date=date(2024, 3, 15),
            season_id=1,
            status=ScheduledGameStatus.SCHEDULED,
        )
        db_session.add(scheduled_game)

        # Add stats with decimal values
        home_stats = TeamSeasonStats(
            team_id=1,
            season_id=1,
            games_played=10,
            wins=7,
            losses=3,
            ppg=85.567,  # Should be rounded to 85.6
            opp_ppg=78.234,  # Should be rounded to 78.2
            win_percentage=0.7,  # Should show as 70.0%
            ft_percentage=0.756,  # Should show as 75.6%
            fg2_percentage=0.523,  # Should show as 52.3%
            fg3_percentage=0.351,  # Should show as 35.1%
        )
        db_session.add(home_stats)
        db_session.commit()

        response = client.get("/scheduled-games/1/matchup")

        assert response.status_code == 200
        assert "85.6" in response.text  # PPG rounded
        assert "78.2" in response.text  # Opp PPG rounded
        assert "70.0%" in response.text  # Win percentage
        assert "75.6%" in response.text  # FT percentage
        assert "52.3%" in response.text  # 2P percentage
        assert "35.1%" in response.text  # 3P percentage
