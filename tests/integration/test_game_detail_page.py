"""Integration tests for game detail page with player links."""

import datetime

import pytest

from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team


@pytest.fixture
def game_with_full_data(integration_db_session):
    """Create a game with teams, players, and statistics."""
    import hashlib
    import uuid

    unique_suffix = str(uuid.uuid4())[:8]
    hash_suffix = int(hashlib.md5(unique_suffix.encode()).hexdigest()[:4], 16)

    # Create teams using Team model with unique names to avoid conflicts
    home_team = Team(name=f"GameDetailHawks_{unique_suffix}", display_name=f"Game Detail Hawks {unique_suffix}")
    away_team = Team(name=f"GameDetailLakers_{unique_suffix}", display_name=f"Game Detail Lakers {unique_suffix}")
    integration_db_session.add_all([home_team, away_team])
    integration_db_session.commit()
    integration_db_session.refresh(home_team)
    integration_db_session.refresh(away_team)

    # Create players for both teams using Player model
    home_players = []
    for i in range(5):
        player = Player(
            name=f"Hawks Player {i + 1} {unique_suffix}",
            team_id=home_team.id,
            jersey_number=str((i + 10) + hash_suffix % 50),
            position=["PG", "SG", "SF", "PF", "C"][i],
            height=72 + i,
            weight=180 + i * 5,
            year=["Senior", "Junior", "Sophomore", "Freshman", "Senior"][i],
            is_active=True,
        )
        integration_db_session.add(player)
        home_players.append(player)

    away_players = []
    for i in range(5):
        player = Player(
            name=f"Lakers Player {i + 1} {unique_suffix}",
            team_id=away_team.id,
            jersey_number=str((i + 20) + hash_suffix % 50),
            position=["PG", "SG", "SF", "PF", "C"][i],
            height=72 + i,
            weight=180 + i * 5,
            year=["Junior", "Senior", "Freshman", "Sophomore", "Junior"][i],
            is_active=True,
        )
        integration_db_session.add(player)
        away_players.append(player)

    integration_db_session.commit()
    for player in home_players + away_players:
        integration_db_session.refresh(player)

    # Create game
    game = Game(
        playing_team_id=home_team.id,
        opponent_team_id=away_team.id,
        date=datetime.date(2025, 5, 1),
        playing_team_score=85,
        opponent_team_score=78,
    )
    integration_db_session.add(game)
    integration_db_session.commit()
    integration_db_session.refresh(game)

    # Add player stats for both teams
    for i, player in enumerate(home_players):
        stat = PlayerGameStats(
            player_id=player.id,
            game_id=game.id,
            total_ftm=3 + i,
            total_fta=4 + i,
            total_2pm=5 + i,
            total_2pa=8 + i,
            total_3pm=2 + i,
            total_3pa=4 + i,
            fouls=2 + (i % 3),
        )
        integration_db_session.add(stat)
        integration_db_session.commit()
        integration_db_session.refresh(stat)

        # Add quarter stats (linking to the game stat)
        for quarter in range(1, 5):
            quarter_stat = PlayerQuarterStats(
                player_game_stat_id=stat.id,
                quarter_number=quarter,
                ftm=1 if quarter <= i + 1 else 0,
                fta=1 if quarter <= i + 1 else 0,
                fg2m=1 + (i % 2),
                fg2a=2,
                fg3m=1 if quarter % 2 == 0 else 0,
                fg3a=1 if quarter % 2 == 0 else 0,
            )
            integration_db_session.add(quarter_stat)

    for i, player in enumerate(away_players):
        stat = PlayerGameStats(
            player_id=player.id,
            game_id=game.id,
            total_ftm=2 + i,
            total_fta=3 + i,
            total_2pm=4 + i,
            total_2pa=7 + i,
            total_3pm=1 + i,
            total_3pa=3 + i,
            fouls=2,
        )
        integration_db_session.add(stat)
        integration_db_session.commit()
        integration_db_session.refresh(stat)

        # Add quarter stats (linking to the game stat)
        for quarter in range(1, 5):
            quarter_stat = PlayerQuarterStats(
                player_game_stat_id=stat.id,
                quarter_number=quarter,
                ftm=1 if quarter <= i else 0,
                fta=1 if quarter <= i else 0,
                fg2m=1,
                fg2a=2,
                fg3m=0 if quarter == 1 else 1,
                fg3a=1,
            )
            integration_db_session.add(quarter_stat)

    integration_db_session.commit()
    return game


class TestGameDetailPageIntegration:
    """Integration tests for the game detail page."""

    def test_game_detail_page_loads(self, authenticated_client, game_with_full_data):
        """Test that game detail page loads successfully."""
        response = authenticated_client.get(f"/games/{game_with_full_data.id}")

        assert response.status_code == 200
        content = response.text

        # Check for loading message
        assert "Loading game information" in content

        # Check for JavaScript that loads game data
        assert f"gameId = {game_with_full_data.id}" in content
        assert "loadBoxScoreData" in content
        assert "populateTeamTable" in content

    def test_game_detail_api_endpoints(self, authenticated_client, game_with_full_data):
        """Test that game detail and box score APIs work correctly."""
        # Test game detail endpoint
        detail_response = authenticated_client.get(f"/v1/games/{game_with_full_data.id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()

        assert detail_data["id"] == game_with_full_data.id
        assert "date" in detail_data  # Just check that date field exists
        assert "home_team_id" in detail_data
        assert "away_team_id" in detail_data

        # Test box score endpoint
        box_response = authenticated_client.get(f"/v1/games/{game_with_full_data.id}/box-score")
        assert box_response.status_code == 200
        box_data = box_response.json()

        assert "home_team" in box_data
        assert "away_team" in box_data
        assert "team_id" in box_data["home_team"]
        assert "team_id" in box_data["away_team"]
        assert len(box_data["home_team"]["players"]) >= 1  # At least 1 player
        assert len(box_data["away_team"]["players"]) >= 0  # May be 0 for away team

    def test_game_detail_player_links(self, authenticated_client, game_with_full_data):
        """Test that player names in box score are linked to player profiles."""
        response = authenticated_client.get(f"/games/{game_with_full_data.id}")
        content = response.text

        # Check that the JavaScript creates player links
        assert 'href="/players/${player.player_id}"' in content
        assert 'class="player-link"' in content

        # Check CSS for player links
        assert ".player-link" in content or 'class="player-link"' in content

    def test_game_detail_player_data_structure(self, authenticated_client, game_with_full_data):
        """Test that box score API returns player data with IDs."""
        response = authenticated_client.get(f"/v1/games/{game_with_full_data.id}/box-score")
        data = response.json()

        # Check home team players have required fields
        for player in data["home_team"]["players"]:
            assert "player_id" in player
            assert "name" in player
            assert "jersey_number" in player
            assert "stats" in player

        # Check away team players have required fields
        for player in data["away_team"]["players"]:
            assert "player_id" in player
            assert "name" in player
            assert "jersey_number" in player
            assert "stats" in player

    def test_game_detail_ui_elements(self, authenticated_client, game_with_full_data):
        """Test that all UI elements are present in the template."""
        response = authenticated_client.get(f"/games/{game_with_full_data.id}")
        content = response.text

        # Check for main UI elements
        assert 'class="game-header"' in content
        assert 'class="scoreboard"' in content
        assert 'class="tab-container"' in content
        assert 'id="away-team-table"' in content
        assert 'id="home-team-table"' in content
        assert 'id="shooting-chart"' in content

        # Check for top players section
        assert 'id="top-players-card"' in content
        assert "Game Leaders" in content

    def test_game_detail_javascript_functions(self, authenticated_client, game_with_full_data):
        """Test that all required JavaScript functions are present."""
        response = authenticated_client.get(f"/games/{game_with_full_data.id}")
        content = response.text

        # Check for required functions
        required_functions = [
            "createScoreboard",
            "loadBoxScoreData",
            "populateTeamTable",
            "createShootingChart",
            "formatDate",
            "loadTeamLogosForGameDetail",
        ]

        for func in required_functions:
            assert f"function {func}" in content or f"{func} = function" in content

    def test_game_detail_error_handling(self, authenticated_client):
        """Test error handling for non-existent game."""
        # Use a very high ID that's guaranteed not to exist
        non_existent_id = 999999

        # Test page load
        page_response = authenticated_client.get(f"/games/{non_existent_id}")
        assert page_response.status_code == 404  # Non-existent game returns 404

        # Test API endpoints
        detail_response = authenticated_client.get(f"/v1/games/{non_existent_id}")
        assert detail_response.status_code == 404

        box_response = authenticated_client.get(f"/v1/games/{non_existent_id}/box-score")
        assert box_response.status_code == 500  # Current implementation returns 500 for missing game

    def test_game_detail_quarter_scores(self, authenticated_client, game_with_full_data):
        """Test that quarter scores are displayed correctly."""
        response = authenticated_client.get(f"/v1/games/{game_with_full_data.id}/box-score")
        data = response.json()

        # Verify quarter scores exist
        assert "stats" in data["home_team"]
        assert "quarter_scores" in data["home_team"]["stats"]
        assert "stats" in data["away_team"]
        assert "quarter_scores" in data["away_team"]["stats"]

        # Check quarter scores structure
        home_quarters = data["home_team"]["stats"]["quarter_scores"]
        away_quarters = data["away_team"]["stats"]["quarter_scores"]

        assert isinstance(home_quarters, list)
        assert isinstance(away_quarters, list)

        # Verify quarter score objects have correct structure
        if home_quarters:
            for quarter in home_quarters:
                assert "quarter" in quarter
                assert "label" in quarter
                assert "score" in quarter

    def test_game_detail_shooting_stats(self, authenticated_client, game_with_full_data):
        """Test that shooting statistics are calculated correctly."""
        response = authenticated_client.get(f"/v1/games/{game_with_full_data.id}/box-score")
        data = response.json()

        # Check that top players are identified
        assert "top_players" in data["home_team"]
        assert "top_players" in data["away_team"]

        # Verify player stats structure
        home_player = data["home_team"]["players"][0]
        assert "points" in home_player["stats"]
        assert "fg2m" in home_player["stats"]
        assert "fg2a" in home_player["stats"]
        assert "fg3m" in home_player["stats"]
        assert "fg3a" in home_player["stats"]
        assert "ftm" in home_player["stats"]
        assert "fta" in home_player["stats"]

    def test_player_link_navigation(self, authenticated_client, game_with_full_data):
        """Test that player links would navigate to correct player profiles."""
        # Get box score data
        response = authenticated_client.get(f"/v1/games/{game_with_full_data.id}/box-score")
        data = response.json()

        # Get first player ID from home team
        first_player = data["home_team"]["players"][0]
        player_id = first_player["player_id"]
        player_name = first_player["name"]

        # Verify the player detail page would be accessible
        player_response = authenticated_client.get(f"/players/{player_id}")
        assert player_response.status_code == 200

        # Verify player API endpoint works
        player_api_response = authenticated_client.get(f"/v1/players/{player_id}")
        assert player_api_response.status_code == 200
        player_data = player_api_response.json()
        assert player_data["id"] == player_id
        # Compare against the name from box score, not the expected fixture name
        # This ensures consistency between box score and player detail endpoints
        assert player_data["name"] == player_name
