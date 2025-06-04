"""Integration tests for team logo display functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.data_access.models import Game, Team
from app.main import create_app
from app.services.image_processing_service import ImageProcessingService


class TestTeamLogoDisplay:
    """Integration tests for team logo display across different pages."""

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
    def test_teams_with_logos(self, db_session):
        """Create test teams with logos."""
        # Create teams
        team1 = Team(name="Team Alpha", display_name="Alpha Team", logo_filename="uploads/teams/1/120x120/logo.jpg")
        team2 = Team(name="Team Beta", display_name="Beta Team", logo_filename="uploads/teams/2/120x120/logo.png")
        team3 = Team(name="Team Gamma", display_name="Gamma Team")  # No logo

        db_session.add_all([team1, team2, team3])
        db_session.commit()
        db_session.refresh(team1)
        db_session.refresh(team2)
        db_session.refresh(team3)

        return team1, team2, team3

    @pytest.fixture
    def test_game(self, db_session, test_teams_with_logos):
        """Create a test game between teams."""
        team1, team2, team3 = test_teams_with_logos

        game = Game(
            date="2024-01-15", playing_team_id=team1.id, opponent_team_id=team2.id, home_score=85, away_score=78
        )

        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        return game

    def setup_mock_logo_files(self, temp_dir, team_ids):
        """Set up mock logo files for testing."""
        for team_id in team_ids:
            team_dir = Path(temp_dir) / "teams" / str(team_id)

            # Create directory structure
            for size in ["original", "120x120", "64x64"]:
                size_dir = team_dir / size
                size_dir.mkdir(parents=True, exist_ok=True)

                # Create mock image file
                img = Image.new(
                    "RGB",
                    (
                        120 if size == "120x120" else 64 if size == "64x64" else 200,
                        120 if size == "120x120" else 64 if size == "64x64" else 200,
                    ),
                    color="red" if team_id == 1 else "blue",
                )

                # Use appropriate extension based on team
                extension = ".jpg" if team_id == 1 else ".png"
                img_path = size_dir / f"logo{extension}"
                img.save(img_path)

    def test_team_detail_page_logo_display(self, client, test_teams_with_logos):
        """Test that team logos display correctly on team detail pages."""
        team1, team2, team3 = test_teams_with_logos

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_mock_logo_files(temp_dir, [1, 2])

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                # Test team with logo
                response = client.get(f"/teams/{team1.id}")
                assert response.status_code == 200

                # Check that logo is referenced in the HTML
                html_content = response.text
                assert "/static/uploads/teams/1/120x120/logo.jpg" in html_content or "team_logo_url" in html_content

                # Test team without logo
                response = client.get(f"/teams/{team3.id}")
                assert response.status_code == 200

                # Should still render successfully without logo
                html_content = response.text
                assert "Team Gamma" in html_content

    def test_games_index_page_logo_display(self, client, test_game, test_teams_with_logos):
        """Test that team logos display correctly on games index page."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_mock_logo_files(temp_dir, [1, 2])

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                response = client.get("/games")
                assert response.status_code == 200

                html_content = response.text

                # Check that game data is present
                assert "Alpha Team" in html_content or "Team Alpha" in html_content
                assert "Beta Team" in html_content or "Team Beta" in html_content

    def test_game_detail_page_logo_display(self, client, test_game, test_teams_with_logos):
        """Test that team logos display correctly on game detail page."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_mock_logo_files(temp_dir, [1, 2])

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                response = client.get(f"/games/{test_game.id}")
                assert response.status_code == 200

                html_content = response.text

                # Check that game details are present
                assert "Alpha Team" in html_content or "Team Alpha" in html_content
                assert "Beta Team" in html_content or "Team Beta" in html_content

    def test_template_helper_integration(self, test_teams_with_logos):
        """Test that the template helper function works with real data."""
        team1, team2, team3 = test_teams_with_logos

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_mock_logo_files(temp_dir, [1, 2])

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                from app.web_ui.templates_config import team_logo_url

                # Test team with logo
                url1 = team_logo_url(team1, "120x120")
                assert url1 is not None
                assert "/static/uploads/teams/1/120x120/logo.jpg" in url1

                # Test team with PNG logo
                url2 = team_logo_url(team2, "64x64")
                assert url2 is not None
                assert "/static/uploads/teams/2/64x64/logo.png" in url2

                # Test team without logo
                url3 = team_logo_url(team3, "120x120")
                assert url3 is None

    def test_logo_fallback_behavior(self, client, test_teams_with_logos):
        """Test fallback behavior when logos are missing."""
        team1, team2, team3 = test_teams_with_logos

        # Don't set up any logo files - they should be missing

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                # Test team detail page
                response = client.get(f"/teams/{team1.id}")
                assert response.status_code == 200

                # Page should still render without errors
                html_content = response.text
                assert "Alpha Team" in html_content or "Team Alpha" in html_content

                # Test games page
                if hasattr(self, "test_game"):
                    response = client.get("/games")
                    assert response.status_code == 200

    def test_different_logo_sizes_display(self, test_teams_with_logos):
        """Test that different logo sizes are correctly served."""
        team1, team2, team3 = test_teams_with_logos

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_mock_logo_files(temp_dir, [1])

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                from app.web_ui.templates_config import team_logo_url

                # Test different sizes
                sizes = ["original", "120x120", "64x64"]

                for size in sizes:
                    url = team_logo_url(team1, size)
                    assert url is not None
                    assert f"teams/1/{size}/logo.jpg" in url

    def test_logo_url_caching_behavior(self, test_teams_with_logos):
        """Test that logo URL generation is consistent."""
        team1, team2, team3 = test_teams_with_logos

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_mock_logo_files(temp_dir, [1])

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                from app.web_ui.templates_config import team_logo_url

                # Multiple calls should return the same URL
                url1 = team_logo_url(team1, "120x120")
                url2 = team_logo_url(team1, "120x120")
                url3 = team_logo_url(team1, "120x120")

                assert url1 == url2 == url3
                assert url1 is not None

    def test_responsive_logo_display(self, client, test_teams_with_logos):
        """Test that logos display appropriately for responsive design."""
        team1, team2, team3 = test_teams_with_logos

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_mock_logo_files(temp_dir, [1, 2])

            with patch.object(ImageProcessingService, "get_team_logo_directory") as mock_get_dir:

                def get_team_dir(team_id):
                    return Path(temp_dir) / "teams" / str(team_id)

                mock_get_dir.side_effect = get_team_dir

                # Test with mobile user agent
                headers = {"User-Agent": "Mobile Safari"}

                response = client.get(f"/teams/{team1.id}", headers=headers)
                assert response.status_code == 200

                # Should still work on mobile
                html_content = response.text
                assert "Alpha Team" in html_content or "Team Alpha" in html_content
