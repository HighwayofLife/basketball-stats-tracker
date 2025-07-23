"""Simple integration test for scheduled game edit functionality."""

from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.data_access.models import ScheduledGame, ScheduledGameStatus, Season, Team


class TestScheduledGameEditSimple:
    """Simple test case for scheduled game edit functionality."""

    def test_edit_route_exists_and_works(self, authenticated_client: TestClient, db_session):
        """Test that the edit route exists and returns the correct form."""
        # Create minimal test data with unique names to avoid conflicts
        import random
        unique_id = random.randint(10000, 99999)
        
        season = Season(
            name=f"Test Season {unique_id}", code=f"TEST{unique_id}", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_active=True
        )
        home_team = Team(name=f"home_team_{unique_id}", display_name=f"Home Team {unique_id}")
        away_team = Team(name=f"away_team_{unique_id}", display_name=f"Away Team {unique_id}")
        db_session.add_all([season, home_team, away_team])
        db_session.flush()  # Get IDs

        # Create scheduled game
        scheduled_game = ScheduledGame(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            scheduled_date=date(2025, 12, 15),
            scheduled_time=time(19, 0),
            season_id=season.id,
            location="Test Arena",
            notes="Test notes",
            status=ScheduledGameStatus.SCHEDULED,
            is_deleted=False,
        )
        db_session.add(scheduled_game)
        db_session.commit()

        # Test that edit page loads
        response = authenticated_client.get(f"/scheduled-games/{scheduled_game.id}/edit")
        assert response.status_code == 200

        html_content = response.text
        print(f"DEBUG: Looking for location: '{scheduled_game.location}' and notes: '{scheduled_game.notes}'")
        print(f"DEBUG: Schedule game ID: {scheduled_game.id}")
        
        # Check essential elements
        assert "Edit Scheduled Game" in html_content
        assert "Update Game" in html_content
        
        # Check that form fields exist and edit functionality is accessible
        assert 'id="location"' in html_content  # Location field exists
        assert 'id="notes"' in html_content  # Notes field exists  
        assert 'id="game-date"' in html_content  # Date field exists
        assert 'id="game-time"' in html_content  # Time field exists
        # Check that it's in edit mode
        assert 'Update Game' in html_content  # Update button instead of Schedule button

    def test_update_scheduled_game_api(self, authenticated_client: TestClient, db_session):
        """Test that the API endpoint for updating scheduled games works."""
        # Create minimal test data
        season = Season(
            name="Test Season", code="TEST", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_active=True
        )
        home_team = Team(name="home_team", display_name="Home Team")
        away_team = Team(name="away_team", display_name="Away Team")
        db_session.add_all([season, home_team, away_team])
        db_session.flush()

        # Create scheduled game
        scheduled_game = ScheduledGame(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            scheduled_date=date(2025, 12, 15),
            scheduled_time=time(19, 0),
            season_id=season.id,
            location="Original Arena",
            notes="Original notes",
            status=ScheduledGameStatus.SCHEDULED,
        )
        db_session.add(scheduled_game)
        db_session.commit()

        # Update via API
        update_data = {
            "scheduled_date": "2025-12-20",
            "scheduled_time": "20:00",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "season_id": season.id,
            "location": "Updated Arena",
            "notes": "Updated notes",
        }

        response = authenticated_client.put(f"/v1/games/scheduled/{scheduled_game.id}", json=update_data)
        assert response.status_code == 200

        # Verify update via API response 
        response_data = response.json()
        assert response_data["scheduled_date"] == "2025-12-20"
        assert response_data["scheduled_time"] == "20:00"
        assert response_data["location"] == "Updated Arena"
        assert response_data["notes"] == "Updated notes"

        # Also verify via a fresh GET request to ensure persistence
        get_response = authenticated_client.get(f"/v1/games/scheduled/{scheduled_game.id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["scheduled_date"] == "2025-12-20"
        assert get_data["scheduled_time"] == "20:00"
        assert get_data["location"] == "Updated Arena"
        assert get_data["notes"] == "Updated notes"
