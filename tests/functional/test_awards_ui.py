# tests/functional/test_awards_ui.py

from datetime import date


def create_test_data(session):
    """Create basic test data for awards UI tests."""
    from app.data_access.crud.crud_season import create_season
    from app.data_access.crud.crud_team import create_team

    # Create teams
    team1 = create_team(session, {"name": "UI Test Team 1"})
    team2 = create_team(session, {"name": "UI Test Team 2"})

    # Create seasons
    season1 = create_season(
        session,
        {
            "name": "2024 Season",
            "code": "2024",
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "is_active": True,
        },
    )

    session.commit()

    return {"teams": [team1, team2], "seasons": [season1]}


class TestPlayerAwardsUI:
    """UI tests for Player of the Week awards display."""

    def test_player_detail_shows_awards(self, client, integration_db_session, authenticated_client):
        """Test that player detail page shows POTW awards."""
        session = integration_db_session

        # Create test data
        test_data = create_test_data(session)
        team1 = test_data["teams"][0]

        # Create player with awards
        from app.data_access.crud.crud_player import create_player

        player = create_player(
            session, {"name": "Award Winner", "team_id": team1.id, "jersey_number": "99", "position": "PG"}
        )

        # Set some awards
        player.player_of_the_week_awards = 3
        session.commit()

        # Get player detail page
        response = authenticated_client.get(f"/players/{player.id}")
        assert response.status_code == 200

        # Check that awards are displayed
        content = response.text
        assert "Player of the Week: 3" in content
        assert "fas fa-star text-warning" in content  # Star icon

    def test_player_detail_hides_zero_awards(self, client, integration_db_session, authenticated_client):
        """Test that player detail page hides awards when count is zero."""
        session = integration_db_session

        # Create test data
        test_data = create_test_data(session)
        team1 = test_data["teams"][0]

        # Create player with no awards
        from app.data_access.crud.crud_player import create_player

        player = create_player(
            session, {"name": "No Awards", "team_id": team1.id, "jersey_number": "00", "position": "SG"}
        )

        # Ensure no awards (default should be 0)
        assert player.player_of_the_week_awards == 0
        session.commit()

        # Get player detail page
        response = authenticated_client.get(f"/players/{player.id}")
        assert response.status_code == 200

        # Check that awards are NOT displayed
        content = response.text
        assert "Player of the Week:" not in content
        assert "fas fa-star text-warning" not in content

    def test_player_stats_api_includes_awards(self, client, integration_db_session):
        """Test that player stats API endpoint includes award count."""
        session = integration_db_session

        # Create test data
        test_data = create_test_data(session)
        team1 = test_data["teams"][0]

        # Create player with awards
        from app.data_access.crud.crud_player import create_player

        player = create_player(
            session, {"name": "API Test Player", "team_id": team1.id, "jersey_number": "88", "position": "C"}
        )

        # Set awards
        player.player_of_the_week_awards = 5
        session.commit()

        # Call API endpoint
        response = client.get(f"/v1/players/{player.id}/stats")
        assert response.status_code == 200

        data = response.json()
        assert "player" in data
        assert data["player"]["player_of_the_week_awards"] == 5

    def test_multiple_players_awards_display(self, client, integration_db_session, authenticated_client):
        """Test awards display for multiple players with different award counts."""
        session = integration_db_session

        # Create test data
        test_data = create_test_data(session)
        team1 = test_data["teams"][0]

        # Create players with different award counts
        from app.data_access.crud.crud_player import create_player

        player1 = create_player(
            session, {"name": "Star Player", "team_id": team1.id, "jersey_number": "1", "position": "PG"}
        )
        player1.player_of_the_week_awards = 10

        player2 = create_player(
            session, {"name": "Good Player", "team_id": team1.id, "jersey_number": "2", "position": "SG"}
        )
        player2.player_of_the_week_awards = 1

        player3 = create_player(
            session, {"name": "New Player", "team_id": team1.id, "jersey_number": "3", "position": "SF"}
        )
        player3.player_of_the_week_awards = 0

        session.commit()

        # Check each player's page
        response1 = authenticated_client.get(f"/players/{player1.id}")
        assert response1.status_code == 200
        assert "Player of the Week: 10" in response1.text

        response2 = authenticated_client.get(f"/players/{player2.id}")
        assert response2.status_code == 200
        assert "Player of the Week: 1" in response2.text

        response3 = authenticated_client.get(f"/players/{player3.id}")
        assert response3.status_code == 200
        assert "Player of the Week:" not in response3.text

    def test_player_list_includes_awards_in_response(self, client, integration_db_session):
        """Test that player list/search endpoints include award data."""
        session = integration_db_session

        # Create test data
        test_data = create_test_data(session)
        team1 = test_data["teams"][0]

        # Create player with awards
        from app.data_access.crud.crud_player import create_player

        player = create_player(
            session, {"name": "List Test Player", "team_id": team1.id, "jersey_number": "77", "position": "PF"}
        )
        player.player_of_the_week_awards = 7
        session.commit()

        # Test players list endpoint
        response = client.get("/v1/players")
        assert response.status_code == 200

        data = response.json()
        # Find our player in the list
        test_player_data = None
        for p in data:
            if p["id"] == player.id:
                test_player_data = p
                break

        assert test_player_data is not None
        assert test_player_data["player_of_the_week_awards"] == 7


class TestAwardsDataIntegrity:
    """Tests to ensure awards data integrity in various scenarios."""

    def test_award_count_persists_after_player_update(self, integration_db_session):
        """Test that award counts persist when player data is updated."""
        session = integration_db_session

        # Create test data
        test_data = create_test_data(session)
        team1 = test_data["teams"][0]

        from app.data_access.crud.crud_player import create_player, update_player

        player = create_player(
            session, {"name": "Persistence Test", "team_id": team1.id, "jersey_number": "66", "position": "C"}
        )

        # Set awards
        player.player_of_the_week_awards = 4
        session.commit()
        original_awards = player.player_of_the_week_awards

        # Update other player data
        update_data = {"name": "Updated Name", "position": "PF", "height": 200, "weight": 90}
        updated_player = update_player(session, player.id, update_data)

        # Awards should remain unchanged
        assert updated_player.player_of_the_week_awards == original_awards

        # Verify in fresh query
        session.refresh(player)
        assert player.player_of_the_week_awards == original_awards

    def test_awards_default_to_zero_for_new_players(self, integration_db_session):
        """Test that new players have zero awards by default."""
        session = integration_db_session

        # Create test data
        test_data = create_test_data(session)
        team1 = test_data["teams"][0]

        from app.data_access.crud.crud_player import create_player

        player = create_player(
            session, {"name": "New Player", "team_id": team1.id, "jersey_number": "55", "position": "PG"}
        )

        # Should default to 0
        assert player.player_of_the_week_awards == 0

        # Verify after commit and refresh
        session.commit()
        session.refresh(player)
        assert player.player_of_the_week_awards == 0
