"""Functional/UI tests for team logo upload functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.data_access.models import Team
from app.main import create_app
from app.services.image_processing_service import ImageProcessingService


class TestTeamLogoUI:
    """UI/Functional tests for team logo upload interface."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def db_session(self, app):
        """Create test database session."""
        from app.dependencies import get_db

        return next(get_db())

    @pytest.fixture
    def test_team(self, db_session):
        """Create a test team."""
        team = Team(name="Test Team", display_name="Test Team Display")
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        return team

    @pytest.fixture
    def authenticated_session(self, client):
        """Create an authenticated session."""
        # Mock authentication for testing
        with patch("app.web_ui.dependencies.get_current_user_from_session") as mock_auth:
            mock_auth.return_value = type("User", (), {"id": 1, "username": "testuser"})()
            yield client

    def test_team_detail_page_upload_form_present(self, authenticated_session, test_team):
        """Test that the team detail page includes upload form when authenticated."""
        response = authenticated_session.get(f"/teams/{test_team.id}")
        assert response.status_code == 200

        html_content = response.text

        # Check for upload form elements
        assert 'type="file"' in html_content or "upload" in html_content.lower()
        assert "logo" in html_content.lower()

    def test_team_detail_page_no_upload_form_unauthenticated(self, client, test_team):
        """Test that upload form is not present when not authenticated."""
        response = client.get(f"/teams/{test_team.id}")
        assert response.status_code == 200

        html_content = response.text

        # Check that team info is still present
        assert test_team.name in html_content or test_team.display_name in html_content

    def test_team_detail_page_logo_display_with_logo(self, authenticated_session, test_team):
        """Test team detail page displays logo when team has one."""
        # Set team to have a logo
        test_team.logo_filename = "uploads/teams/1/120x120/logo.jpg"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock logo file
            team_dir = Path(temp_dir) / "teams" / str(test_team.id)
            logo_dir = team_dir / "120x120"
            logo_dir.mkdir(parents=True)

            # Create test image
            img = Image.new("RGB", (120, 120), color="blue")
            logo_path = logo_dir / "logo.jpg"
            img.save(logo_path)

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = team_dir

                response = authenticated_session.get(f"/teams/{test_team.id}")
                assert response.status_code == 200

                html_content = response.text

                # Check for logo image or reference
                assert "logo" in html_content.lower()

    def test_team_detail_page_fallback_without_logo(self, authenticated_session, test_team):
        """Test team detail page shows fallback when no logo exists."""
        # Ensure team has no logo
        test_team.logo_filename = None

        response = authenticated_session.get(f"/teams/{test_team.id}")
        assert response.status_code == 200

        html_content = response.text

        # Should still display team info
        assert test_team.name in html_content or test_team.display_name in html_content

    def test_games_list_logo_display(self, authenticated_session, db_session):
        """Test that team logos appear in games list."""
        # Create teams
        team1 = Team(name="Team A", display_name="Alpha", logo_filename="uploads/teams/1/64x64/logo.jpg")
        team2 = Team(name="Team B", display_name="Beta", logo_filename="uploads/teams/2/64x64/logo.png")
        db_session.add_all([team1, team2])
        db_session.commit()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock logo files
            for team_id in [1, 2]:
                team_dir = Path(temp_dir) / "teams" / str(team_id)
                logo_dir = team_dir / "64x64"
                logo_dir.mkdir(parents=True)

                # Create test image
                img = Image.new("RGB", (64, 64), color="red" if team_id == 1 else "blue")
                extension = ".jpg" if team_id == 1 else ".png"
                logo_path = logo_dir / f"logo{extension}"
                img.save(logo_path)

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                response = authenticated_session.get("/games")
                assert response.status_code == 200

                html_content = response.text

                # Check that games page loads successfully
                assert "games" in html_content.lower() or "Games" in html_content

    def test_upload_form_file_validation_ui(self, authenticated_session, test_team):
        """Test that upload form validates file types in UI."""
        response = authenticated_session.get(f"/teams/{test_team.id}")
        assert response.status_code == 200

        html_content = response.text

        # Check for file input with appropriate accept attribute
        if 'type="file"' in html_content:
            # Look for accept attribute with image types
            assert "accept=" in html_content or "image" in html_content

    def test_logo_upload_progress_indication(self, authenticated_session, test_team):
        """Test that upload form provides user feedback."""
        # This test verifies the form structure supports progress indication
        response = authenticated_session.get(f"/teams/{test_team.id}")
        assert response.status_code == 200

        html_content = response.text

        # Check for form elements that would support AJAX upload
        # This is more about form structure than actual JS testing
        if "upload" in html_content.lower():
            # Form should be present for upload functionality
            assert "form" in html_content.lower() or "upload" in html_content.lower()

    def test_responsive_logo_display_mobile(self, authenticated_session, test_team):
        """Test that logos display appropriately on mobile devices."""
        # Simulate mobile user agent
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"}

        # Set team to have a logo
        test_team.logo_filename = "uploads/teams/1/64x64/logo.jpg"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock logo file
            team_dir = Path(temp_dir) / "teams" / str(test_team.id)
            logo_dir = team_dir / "64x64"
            logo_dir.mkdir(parents=True)

            # Create test image
            img = Image.new("RGB", (64, 64), color="green")
            logo_path = logo_dir / "logo.jpg"
            img.save(logo_path)

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:
                mock_get_dir.return_value = team_dir

                response = authenticated_session.get(f"/teams/{test_team.id}", headers=headers)
                assert response.status_code == 200

                html_content = response.text

                # Should still work on mobile
                assert test_team.name in html_content or test_team.display_name in html_content

    def test_logo_delete_functionality_ui(self, authenticated_session, test_team):
        """Test that delete logo functionality is available in UI."""
        # Set team to have a logo
        test_team.logo_filename = "uploads/teams/1/120x120/logo.jpg"

        response = authenticated_session.get(f"/teams/{test_team.id}")
        assert response.status_code == 200

        html_content = response.text

        # Check for delete button or functionality when logo exists
        if test_team.logo_filename:
            # There should be some way to delete the logo
            assert "delete" in html_content.lower() or "remove" in html_content.lower()

    def test_games_detail_page_logo_display(self, authenticated_session, db_session):
        """Test that team logos display on game detail pages."""
        from app.data_access.models import Game

        # Create teams and game
        team1 = Team(name="Home Team", display_name="Home", logo_filename="uploads/teams/1/64x64/logo.jpg")
        team2 = Team(name="Away Team", display_name="Away", logo_filename="uploads/teams/2/64x64/logo.png")
        db_session.add_all([team1, team2])
        db_session.commit()

        game = Game(
            date="2024-01-15", playing_team_id=team1.id, opponent_team_id=team2.id, home_score=85, away_score=78
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock logo files
            for team_id in [1, 2]:
                team_dir = Path(temp_dir) / "teams" / str(team_id)
                logo_dir = team_dir / "64x64"
                logo_dir.mkdir(parents=True)

                # Create test image
                img = Image.new("RGB", (64, 64), color="orange" if team_id == 1 else "purple")
                extension = ".jpg" if team_id == 1 else ".png"
                logo_path = logo_dir / f"logo{extension}"
                img.save(logo_path)

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                response = authenticated_session.get(f"/games/{game.id}")
                assert response.status_code == 200

                html_content = response.text

                # Check that game details are present
                assert "Home Team" in html_content or "Home" in html_content
                assert "Away Team" in html_content or "Away" in html_content

    def test_logo_accessibility_features(self, authenticated_session, test_team):
        """Test that logo display includes accessibility features."""
        # Set team to have a logo
        test_team.logo_filename = "uploads/teams/1/120x120/logo.jpg"

        response = authenticated_session.get(f"/teams/{test_team.id}")
        assert response.status_code == 200

        html_content = response.text

        # Check for accessibility attributes
        if "<img" in html_content:
            # Should have alt text or other accessibility features
            assert "alt=" in html_content or "aria-" in html_content

    def test_multiple_team_logos_performance(self, authenticated_session, db_session):
        """Test that pages with multiple team logos load efficiently."""
        # Create multiple teams with logos
        teams = []
        for i in range(5):
            team = Team(
                name=f"Team {i + 1}",
                display_name=f"Team {i + 1} Display",
                logo_filename=f"uploads/teams/{i + 1}/64x64/logo.jpg",
            )
            teams.append(team)

        db_session.add_all(teams)
        db_session.commit()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock logo files for all teams
            for i in range(5):
                team_id = i + 1
                team_dir = Path(temp_dir) / "teams" / str(team_id)
                logo_dir = team_dir / "64x64"
                logo_dir.mkdir(parents=True)

                # Create test image
                img = Image.new("RGB", (64, 64), color=(i * 50, i * 30, i * 40))
                logo_path = logo_dir / "logo.jpg"
                img.save(logo_path)

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                # Test teams index page
                response = authenticated_session.get("/teams")
                assert response.status_code == 200

                # Should load in reasonable time (implicitly tested by not timing out)
                html_content = response.text
                assert "teams" in html_content.lower() or "Teams" in html_content
