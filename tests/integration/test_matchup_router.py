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
        season = Season(id=1, name="2023-24", code="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
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
            season="2023-24",
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
            season="2023-24",
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
        home_player = Player(id=1, name="Home Star", team_id=1, jersey_number="10", position="PG")
        away_player = Player(id=2, name="Away Star", team_id=2, jersey_number="20", position="SG")
        db_session.add_all([home_player, away_player])

        home_player_stats = PlayerSeasonStats(
            player_id=1,
            season="2023-24",
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
            season="2023-24",
            games_played=10,
            total_ftm=40,
            total_fta=55,
            total_2pm=70,
            total_2pa=140,
            total_3pm=20,
            total_3pa=65,
        )
        db_session.add_all([home_player_stats, away_player_stats])

        # Create historical game
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
        season = Season(id=1, name="2023-24", code="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
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
        season = Season(id=1, name="2023-24", code="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
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
            team_id=1,
            season="2023-24",
            games_played=5,
            wins=3,
            losses=2,
            total_points_for=375,
            total_points_against=350,
            total_ftm=75,
            total_fta=100,
            total_2pm=100,
            total_2pa=200,
            total_3pm=25,
            total_3pa=75,
        )
        db_session.add(home_stats)
        db_session.commit()

        response = client.get("/scheduled-games/1/matchup")

        assert response.status_code == 200
        assert "No previous matchups between these teams" in response.text

    def test_view_matchup_multiple_players(self, client: TestClient, db_session):
        """Test matchup view with multiple top players."""
        # Create test data
        season = Season(id=1, name="2023-24", code="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
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
                season="2023-24",
                games_played=10,
                total_ftm=10 * i,
                total_fta=12 * i,
                total_2pm=20 * i,
                total_2pa=40 * i,
                total_3pm=5 * i,
                total_3pa=15 * i,
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
        season = Season(id=1, name="2023-24", code="2023-24", start_date=date(2023, 10, 1), end_date=date(2024, 5, 31))
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
            season="2023-24",
            games_played=10,
            wins=7,
            losses=3,
            total_points_for=856,  # 85.6 PPG
            total_points_against=782,  # 78.2 opp PPG
            total_ftm=756,  # 75.6% FT
            total_fta=1000,
            total_2pm=523,  # 52.3% 2P
            total_2pa=1000,
            total_3pm=351,  # 35.1% 3P
            total_3pa=1000,
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
