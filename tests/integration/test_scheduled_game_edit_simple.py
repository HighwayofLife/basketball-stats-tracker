"""Simple integration test for scheduled game edit functionality."""

from datetime import date, time

from fastapi.testclient import TestClient

from app.data_access.models import ScheduledGame, ScheduledGameStatus, Season, Team


class TestScheduledGameEditSimple:
    """Simple test case for scheduled game edit functionality."""

    def test_edit_route_exists_and_works(self, authenticated_client: TestClient, db_session):
        """Test that the edit route exists and returns the correct form."""
        # Create minimal test data
        season = Season(
            name="Test Season", code="TEST", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_active=True
        )
        home_team = Team(name="home_team", display_name="Home Team")
        away_team = Team(name="away_team", display_name="Away Team")
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
        # Check essential elements
        assert "Edit Scheduled Game" in html_content
        assert "Update Game" in html_content
        assert "Test Arena" in html_content
        assert "Test notes" in html_content

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

        # Verify update
        db_session.expire_all()
        updated_game = db_session.query(ScheduledGame).filter_by(id=scheduled_game.id).first()
        assert updated_game.scheduled_date == date(2025, 12, 20)
        assert updated_game.scheduled_time == time(20, 0)
        assert updated_game.location == "Updated Arena"
        assert updated_game.notes == "Updated notes"
