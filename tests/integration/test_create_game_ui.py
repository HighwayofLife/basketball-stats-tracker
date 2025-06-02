"""Integration tests for the create game UI functionality."""

import os

# Set JWT_SECRET_KEY for all tests in this module
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"

import requests
from bs4 import BeautifulSoup

from tests.integration.test_ui_validation import BASE_URL


class TestCreateGameUI:
    """Test the create game UI page functionality."""

    def test_create_game_page_loads(self, docker_containers):
        """Test that the create game page loads successfully."""
        response = requests.get(f"{BASE_URL}/games/create")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_create_game_page_structure(self, docker_containers):
        """Test that the create game page has correct form structure."""
        response = requests.get(f"{BASE_URL}/games/create")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for page title
        title = soup.find("h1")
        assert title is not None
        assert "Schedule Game" in title.text

        # Check for form
        form = soup.find("form", id="create-game-form")
        assert form is not None

        # Check for required form fields
        date_input = soup.find("input", {"id": "game-date"})
        assert date_input is not None
        assert date_input.get("type") == "date"
        assert date_input.get("required") is not None

        time_input = soup.find("input", {"id": "game-time"})
        assert time_input is not None
        assert time_input.get("type") == "time"

        home_team_select = soup.find("select", {"id": "home-team"})
        assert home_team_select is not None
        assert home_team_select.get("required") is not None

        away_team_select = soup.find("select", {"id": "away-team"})
        assert away_team_select is not None
        assert away_team_select.get("required") is not None

        location_input = soup.find("input", {"id": "location"})
        assert location_input is not None

        notes_textarea = soup.find("textarea", {"id": "notes"})
        assert notes_textarea is not None

        # Check for submit button
        submit_button = soup.find("button", {"type": "submit"})
        assert submit_button is not None
        assert "Schedule" in submit_button.text

    def test_create_game_page_javascript(self, docker_containers):
        """Test that the create game page has correct JavaScript for API calls."""
        response = requests.get(f"{BASE_URL}/games/create")
        content = response.text

        # Check that JavaScript uses correct API endpoint for scheduled games
        assert "/v1/games/scheduled" in content
        assert "POST" in content
        assert "scheduled_date" in content

        # Check for authentication
        assert "credentials: 'include'" in content

        # Check for success handling
        assert "window.location.href = '/games'" in content
        assert "alert('Game scheduled successfully!')" in content

    def test_create_game_form_validation(self, docker_containers):
        """Test client-side form validation requirements."""
        response = requests.get(f"{BASE_URL}/games/create")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check JavaScript validation
        scripts = soup.find_all("script")
        script_content = "\n".join(script.text for script in scripts if script.text)

        # Should validate that home and away teams are different
        assert "homeTeamId === awayTeamId" in script_content
        assert "same team" in script_content.lower()

        # Should validate required fields
        assert "required" in str(soup.find("input", {"id": "game-date"}))
        assert "required" in str(soup.find("select", {"id": "home-team"}))
        assert "required" in str(soup.find("select", {"id": "away-team"}))

    def test_create_game_team_options(self, docker_containers):
        """Test that team selection dropdowns are populated."""
        response = requests.get(f"{BASE_URL}/games/create")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find script that populates teams
        scripts = soup.find_all("script")
        script_content = "\n".join(script.text for script in scripts if script.text)

        # Should fetch teams from API
        assert "/v1/teams/list" in script_content
        assert "fetch" in script_content

        # Should populate both select elements
        assert "home-team" in script_content
        assert "away-team" in script_content
        assert "appendChild" in script_content or "innerHTML" in script_content

    def test_create_game_date_defaults(self, docker_containers):
        """Test that the date field has appropriate defaults."""
        response = requests.get(f"{BASE_URL}/games/create")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for script that sets default date
        scripts = soup.find_all("script")
        script_content = "\n".join(script.text for script in scripts if script.text)

        # Should set today as default or have date handling
        assert "new Date()" in script_content or "toISOString()" in script_content

    def test_create_game_error_handling(self, docker_containers):
        """Test that the form has proper error handling."""
        response = requests.get(f"{BASE_URL}/games/create")
        content = response.text

        # Should handle API errors
        assert "catch" in content
        assert "error" in content.lower()
        assert "alert" in content or "console.error" in content

        # Should handle team loading errors
        assert "Failed to load teams" in content or "Error loading teams" in content

    def test_navigation_to_create_game(self, docker_containers):
        """Test navigation from games list to create game page."""
        # Get games list page
        response = requests.get(f"{BASE_URL}/games")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find link to create/schedule game
        create_link = soup.find("a", href="/games/create")
        assert create_link is not None
        assert "Schedule Game" in create_link.text

    def test_create_game_authentication_check(self, docker_containers):
        """Test that create game page checks authentication status."""
        response = requests.get(f"{BASE_URL}/games/create")
        content = response.text

        # Should include authentication checks
        assert "checkAuth" in content or "isAuthenticated" in content or "getCurrentUser" in content

        # Should handle unauthenticated users
        assert "/login" in content or "sign in" in content.lower()
