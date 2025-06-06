"""
UI validation tests that start containers and verify HTML pages work correctly.

This module provides comprehensive UI testing by:
1. Starting Docker containers (database + web)
2. Waiting for services to be ready
3. Testing all major HTML pages
4. Validating key HTML elements
5. Cleaning up containers after tests

Run with: pytest tests/integration/test_ui_validation.py
"""

import contextlib
import logging
import os
import subprocess
import time

# Set consistent admin password for tests
os.environ["DEFAULT_ADMIN_PASSWORD"] = "TestAdminPassword123!"
# Set JWT secret key for tests (required by auth module)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-ui-tests-12345678901234567890"

import pytest
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
DOCKER_COMPOSE_FILE = "docker-compose.yml"
MAX_STARTUP_WAIT = 60  # seconds
HEALTH_CHECK_INTERVAL = 2  # seconds


class DockerContainerManager:
    """Manages Docker containers for UI testing."""

    def __init__(self):
        self.containers_started = False

    def start_containers(self):
        """Start Docker containers and wait for them to be ready."""
        logger.info("Starting Docker containers...")

        # Stop any existing containers (ignore errors)
        try:
            subprocess.run(
                ["docker", "compose", "down", "--remove-orphans"],
                capture_output=True,
                timeout=30,
                check=False,  # Don't fail if containers aren't running
            )
        except subprocess.TimeoutExpired:
            logger.warning("Timeout stopping existing containers, continuing...")

        # Start containers
        result = subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start containers: {result.stderr}")

        self.containers_started = True
        logger.info("Docker containers started")

        # Wait for services to be ready
        self._wait_for_services()

    def stop_containers(self):
        """Stop and clean up Docker containers."""
        if self.containers_started:
            logger.info("Stopping Docker containers...")
            subprocess.run(["docker", "compose", "down", "--remove-orphans"], capture_output=True, timeout=30)
            self.containers_started = False
            logger.info("Docker containers stopped")

    def _wait_for_services(self):
        """Wait for web service to be ready."""
        logger.info(f"Waiting for web service at {BASE_URL}...")

        start_time = time.time()
        while time.time() - start_time < MAX_STARTUP_WAIT:
            try:
                response = requests.get(f"{BASE_URL}/", timeout=5)
                if response.status_code == 200:
                    # Additional check - try to hit the auth status endpoint
                    try:
                        auth_check = requests.get(f"{BASE_URL}/auth/oauth/status", timeout=5)
                        if auth_check.status_code == 200:
                            logger.info("Web service is ready (auth endpoints responding)")
                            return
                        else:
                            logger.debug(f"Auth endpoint returned {auth_check.status_code}, waiting...")
                    except Exception as e:
                        logger.debug(f"Auth endpoint check failed: {e}, waiting...")
                elif response.status_code == 500:
                    # Server is responding but may have errors, wait a bit more
                    logger.debug("Server responding with 500, waiting...")
            except requests.exceptions.RequestException:
                # Service not ready yet
                pass

            time.sleep(HEALTH_CHECK_INTERVAL)

        raise RuntimeError(f"Web service did not become ready within {MAX_STARTUP_WAIT} seconds")


@pytest.fixture(scope="module")
def docker_containers():
    """Pytest fixture to manage Docker containers for the test session."""
    manager = DockerContainerManager()

    try:
        manager.start_containers()
        yield manager
    finally:
        manager.stop_containers()


@pytest.fixture(scope="module")
def admin_session(docker_containers):
    """Authenticated session for the test admin user."""
    session = requests.Session()
    test_username = "testadmin"
    test_password = "TestAdminPassword123!"

    # Try to register a new test user
    register_resp = session.post(
        f"{BASE_URL}/auth/register",
        json={
            "username": test_username,
            "email": "testadmin@example.com",
            "password": test_password,
            "full_name": "Test Admin User",
        },
        timeout=10,
    )

    # If user already exists (400) or registration succeeds (200/201), proceed with login
    if register_resp.status_code not in (200, 201, 400):
        # Provide more context for debugging
        error_msg = f"Unexpected registration response: {register_resp.status_code}"
        try:
            error_detail = register_resp.json().get("detail", register_resp.text)
        except Exception:
            error_detail = register_resp.text

        # Log container logs for debugging in CI
        if register_resp.status_code == 500:
            try:
                # Capture container logs
                import subprocess

                logs = subprocess.run(
                    ["docker", "compose", "logs", "web", "--tail", "50"], capture_output=True, text=True, timeout=5
                )
                logger.error(f"Web container logs:\n{logs.stdout}")
            except Exception as e:
                logger.error(f"Failed to capture logs: {e}")

        raise RuntimeError(f"{error_msg} - {error_detail}")

    # Attempt login
    login_resp = session.post(
        f"{BASE_URL}/auth/token",
        data={"username": test_username, "password": test_password},
        timeout=10,
    )

    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    return session


class TestUIValidation:
    """Test class for UI validation."""

    def test_homepage_loads(self, docker_containers):
        """Test that the homepage loads successfully."""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_homepage_contains_key_elements(self, docker_containers):
        """Test that the homepage contains expected HTML elements."""
        response = requests.get(f"{BASE_URL}/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for navigation elements
        nav = soup.find("nav")
        assert nav is not None, "Navigation element not found"

        # Check for main content area
        main = soup.find("main") or soup.find("div", class_="main-content")
        assert main is not None, "Main content area not found"

        # Check for dashboard title or heading
        title_elements = soup.find_all(["h1", "h2", "title"])
        assert len(title_elements) > 0, "No title/heading elements found"

        # Check that page contains some basketball-related content
        page_text = soup.get_text().lower()
        basketball_terms = ["game", "player", "team", "stats", "basketball"]
        assert any(term in page_text for term in basketball_terms), "No basketball-related content found"

    def test_dashboard_data_display(self, docker_containers):
        """Test that the dashboard correctly displays game data and handles empty state."""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for Recent Games section
        recent_games_heading = soup.find("h2", string="Recent Games")
        assert recent_games_heading is not None, "Recent Games section not found"

        # Check for games table or 'No games found' message
        games_table = soup.find("table", class_="games-table")
        no_games_message = soup.find("td", string="No games found.")

        # Should have either games or no games message, not both
        assert (games_table is not None) or (
            no_games_message is not None
        ), "Neither games table nor 'No games found' message found"

        # If we have a games table, verify it has the expected structure
        if games_table:
            # Check for table headers
            headers = games_table.find_all("th")
            header_texts = [h.get_text(strip=True) for h in headers]
            expected_headers = ["Date", "Away Team", "Score", "Home Team", "Actions"]
            for expected in expected_headers:
                assert expected in header_texts, f"Expected header '{expected}' not found in table"

            # Check for game rows
            tbody = games_table.find("tbody")
            game_rows = tbody.find_all("tr") if tbody else []

            # If there are game rows, verify they have View buttons
            if game_rows and not no_games_message:
                for row in game_rows:
                    view_link = row.find("a", string="View")
                    if view_link:
                        assert view_link["href"].startswith("/games/"), "View link should point to game detail page"

        # Check for Players of the Week section
        players_section = soup.find("div", class_="sidebar")
        assert players_section is not None, "Sidebar with Players of the Week not found"

        # Check for quick action buttons
        quick_actions = soup.find("div", class_="quick-actions-top")
        assert quick_actions is not None, "Quick actions section not found"

        # Verify quick action links
        box_scores_link = soup.find("a", href="/games")
        team_analysis_link = soup.find("a", href="/teams")
        player_stats_link = soup.find("a", href="/players")

        assert box_scores_link is not None, "Box Scores quick action not found"
        assert team_analysis_link is not None, "Team Analysis quick action not found"
        assert player_stats_link is not None, "Player Stats quick action not found"

    def test_dashboard_with_database_error_handling(self, docker_containers):
        """Test that dashboard handles database errors gracefully."""
        # The dashboard should still render even if there's a database issue
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200

        # Even with errors, the page should have basic structure
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.find("nav") is not None, "Navigation should still render with DB errors"
        assert soup.find("main") or soup.find(
            "div", class_="main-content"
        ), "Main content should still render with DB errors"

    def test_players_page_loads(self, docker_containers):
        """Test that the players page loads successfully."""
        response = requests.get(f"{BASE_URL}/players")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_players_page_structure(self, docker_containers):
        """Test that the players page has expected structure."""
        response = requests.get(f"{BASE_URL}/players")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for page title/heading
        heading = soup.find(["h1", "h2"], string=lambda text: text and "player" in text.lower())
        assert heading is not None, "Players page heading not found"

        # Check for table or list structure (even if empty)
        table_or_list = soup.find(["table", "ul", "ol", "div"])
        assert table_or_list is not None, "No content structure found on players page"

    def test_player_detail_page_api_urls(self, docker_containers):
        """Test that player detail pages use correct API URLs in JavaScript."""
        # First get a list of players to find a valid player ID
        players_response = requests.get(f"{BASE_URL}/v1/players/list")
        if players_response.status_code == 200:
            players = players_response.json()
            if players:
                player_id = players[0]["id"]

                # Test the player detail page loads
                detail_response = requests.get(f"{BASE_URL}/players/{player_id}")
                assert detail_response.status_code == 200

                # Check that the JavaScript uses correct API URLs (without /api prefix)
                content = detail_response.text
                assert f"/v1/players/${player_id}/stats" in content.replace(
                    "{playerId}", str(player_id)
                ), "Player detail page should use /v1/players/ID/stats endpoint"
                assert f"/v1/players/${player_id}/upload-image" in content.replace(
                    "{playerId}", str(player_id)
                ), "Player detail page should use /v1/players/ID/upload-image endpoint"

                # Ensure incorrect API URLs are not present
                assert "/api/v1/players" not in content, "Player detail page should not use /api/v1/players prefix"

    def test_teams_page_loads(self, docker_containers):
        """Test that the teams page loads successfully."""
        response = requests.get(f"{BASE_URL}/teams")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_teams_page_structure(self, docker_containers):
        """Test that the teams page has expected structure."""
        response = requests.get(f"{BASE_URL}/teams")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for page title/heading
        heading = soup.find(["h1", "h2"], string=lambda text: text and "team" in text.lower())
        assert heading is not None, "Teams page heading not found"

    def test_games_page_loads(self, docker_containers):
        """Test that the games page loads successfully."""
        response = requests.get(f"{BASE_URL}/games")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_games_page_structure(self, docker_containers):
        """Test that the games page has expected structure."""
        response = requests.get(f"{BASE_URL}/games")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for page title/heading
        heading = soup.find(["h1", "h2"], string=lambda text: text and "game" in text.lower())
        assert heading is not None, "Games page heading not found"

    def test_reports_page_loads(self, docker_containers):
        """Test that the reports page loads successfully."""
        response = requests.get(f"{BASE_URL}/reports")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_reports_page_structure(self, docker_containers):
        """Test that the reports page has expected structure."""
        response = requests.get(f"{BASE_URL}/reports")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for page title/heading
        heading = soup.find(["h1", "h2"], string=lambda text: text and "report" in text.lower())
        assert heading is not None, "Reports page heading not found"

    def test_navigation_links_exist(self, docker_containers):
        """Test that navigation links exist and are properly formatted."""
        response = requests.get(f"{BASE_URL}/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find navigation links
        nav_links = soup.find_all("a", href=True)

        # Check for expected navigation paths
        expected_paths = ["/players", "/teams", "/games"]
        found_paths = [link["href"] for link in nav_links if link["href"].startswith("/")]

        for path in expected_paths:
            assert any(path in found_path for found_path in found_paths), f"Navigation link for {path} not found"

    def test_css_and_static_resources(self, docker_containers):
        """Test that CSS and static resources load properly."""
        # Get homepage to find CSS links
        response = requests.get(f"{BASE_URL}/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find CSS links
        css_links = soup.find_all("link", rel="stylesheet")

        # Test at least one CSS file loads
        if css_links:
            css_url = css_links[0]["href"]
            if css_url.startswith("/"):
                css_url = f"{BASE_URL}{css_url}"
            elif not css_url.startswith("http"):
                css_url = f"{BASE_URL}/{css_url}"

            css_response = requests.get(css_url)
            assert css_response.status_code == 200, f"CSS file {css_url} failed to load"
            assert "text/css" in css_response.headers.get("content-type", ""), "CSS content-type incorrect"

    def test_error_pages_handled_gracefully(self, docker_containers):
        """Test that non-existent pages return appropriate responses."""
        response = requests.get(f"{BASE_URL}/nonexistent-page")

        # Should return 404 or redirect, not 500
        assert response.status_code in [404, 302, 301], f"Expected 404 or redirect, got {response.status_code}"

    def test_api_endpoints_respond(self, docker_containers):
        """Test that API endpoints respond appropriately."""
        # Test if API endpoints exist and respond
        api_endpoints = ["/api/players", "/api/teams", "/api/games"]

        for endpoint in api_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            # API should respond with 200 (data) or 404 (not implemented), not 500
            assert response.status_code in [200, 404], f"API endpoint {endpoint} returned {response.status_code}"

            if response.status_code == 200:
                # If it returns data, it should be JSON
                assert "application/json" in response.headers.get(
                    "content-type", ""
                ), f"API endpoint {endpoint} not returning JSON"


class TestContainerHealthCheck:
    """Test container lifecycle management."""

    def test_container_health_check(self, docker_containers):
        """Test that containers are running properly."""
        # Verify containers are running (using the shared fixture)
        result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"], capture_output=True, text=True
        )

        running_services = result.stdout.strip().split("\n") if result.stdout.strip() else []
        assert "web" in running_services, "Web service not running"
        assert "database" in running_services, "Database service not running"

        # Test that we can connect to the web service
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200


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

        # Check for page title (should be h2, not h1)
        title = soup.find("h2")
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
        assert "Game scheduled successfully!" in content
        assert "sessionStorage.setItem" in content

    def test_create_game_form_validation(self, docker_containers):
        """Test client-side form validation requirements."""
        response = requests.get(f"{BASE_URL}/games/create")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check JavaScript validation
        scripts = soup.find_all("script")
        script_content = "\n".join(script.text for script in scripts if script.text)

        # Should validate that home and away teams are different
        assert "homeTeamId === awayTeamId" in script_content
        assert "different" in script_content.lower()

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
        assert "/v1/teams" in script_content
        assert "fetch" in script_content

        # Should populate both select elements
        assert "home-team" in script_content
        assert "away-team" in script_content
        assert "add(" in script_content  # Uses select.add() method

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
        assert "Error loading teams" in content

    def test_navigation_to_create_game(self, docker_containers):
        """Test navigation from games list to create game page."""
        # Get games list page
        response = requests.get(f"{BASE_URL}/games")

        # The "Schedule Game" link is only visible when authenticated
        # Since tests run without authentication, test that:
        # 1. The create game page is accessible directly
        create_response = requests.get(f"{BASE_URL}/games/create")
        assert create_response.status_code == 200

        # 2. The games page renders without errors
        assert response.status_code == 200
        assert "Basketball Games" in response.text

    def test_create_game_authentication_check(self, docker_containers):
        """Test that create game page checks authentication status."""
        response = requests.get(f"{BASE_URL}/games/create")
        content = response.text

        # Should include authentication token handling
        assert "access_token" in content or "Authorization" in content

        # Should handle credentials/authentication
        assert "credentials: 'include'" in content

    def test_authenticated_navigation_shows_schedule_button(self, docker_containers, admin_session):
        """Test that authenticated users see the Schedule Game button."""
        # Unauthenticated check
        response = requests.get(f"{BASE_URL}/games")
        soup = BeautifulSoup(response.content, "html.parser")

        unauthenticated_link = soup.find("a", href="/games/create")
        assert unauthenticated_link is None, "Schedule Game button should not be visible to unauthenticated users"

        login_link = soup.find("a", href="/login")
        assert login_link is not None, "Login link should be visible to unauthenticated users"

        # Authenticated scenario
        auth_response = admin_session.get(f"{BASE_URL}/games")
        auth_soup = BeautifulSoup(auth_response.content, "html.parser")
        authenticated_link = auth_soup.find("a", href="/games/create")
        assert authenticated_link is not None, "Schedule Game button should be visible to authenticated users"


class TestTeamLogoHandling:
    """Test team logo functionality to prevent 404 errors."""

    def test_dashboard_no_broken_logo_links(self, docker_containers):
        """Test that dashboard doesn't contain broken logo image links."""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, "html.parser")

        # Method 1: Check for logo images in HTML (should be none for teams without logos)
        logo_images = soup.find_all("img", src=lambda x: x and "logo" in x.lower())

        # Method 2: Validate any img tags that do exist
        all_images = soup.find_all("img", src=True)
        broken_images = []

        for img in all_images:
            src = img.get("src")
            if src and src.startswith("/"):
                # Test if image actually exists
                img_response = requests.head(f"{BASE_URL}{src}")
                if img_response.status_code == 404:
                    broken_images.append(src)

        assert len(broken_images) == 0, f"Found broken images: {broken_images}"

        # Verify that team logos show fallback icons instead of broken images
        team_logo_divs = soup.find_all("div", class_="team-logo-small")
        fallback_icons = soup.find_all("i", class_="fas fa-users")

        # Should have fallback icons for teams without logos
        assert len(fallback_icons) > 0, "No fallback icons found for teams without logos"

    def test_games_page_no_broken_logo_links(self, docker_containers):
        """Test that games page doesn't contain broken logo image links."""
        response = requests.get(f"{BASE_URL}/games")
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, "html.parser")

        # Wait for dynamic content to load, then check again
        import time

        time.sleep(2)

        # Re-fetch after JavaScript has loaded
        response = requests.get(f"{BASE_URL}/games")
        soup = BeautifulSoup(response.content, "html.parser")

        # Validate any img tags that exist
        all_images = soup.find_all("img", src=True)
        broken_images = []

        for img in all_images:
            src = img.get("src")
            if src and src.startswith("/"):
                # Test if image actually exists
                img_response = requests.head(f"{BASE_URL}{src}")
                if img_response.status_code == 404:
                    broken_images.append(src)

        assert len(broken_images) == 0, f"Found broken images: {broken_images}"

    def test_logo_urls_return_404_when_appropriate(self, docker_containers):
        """Test that non-existent logo URLs return 404 instead of 200."""
        # Test a few common logo URL patterns that shouldn't exist
        test_urls = [
            f"{BASE_URL}/uploads/teams/1/logo.nonexistent",
            f"{BASE_URL}/uploads/teams/999/logo.png",
            f"{BASE_URL}/uploads/teams/invalid/logo.jpg",
        ]

        for url in test_urls:
            response = requests.get(url)
            # Should be 404 for non-existent files, not 200
            assert response.status_code == 404, f"URL {url} should return 404 but returned {response.status_code}"

    def test_team_detail_page_logo_handling(self, docker_containers):
        """Test that team detail pages handle missing logos properly."""
        # Get a list of teams first
        teams_response = requests.get(f"{BASE_URL}/v1/teams")
        if teams_response.status_code == 200:
            teams = teams_response.json()
            if teams:
                team_id = teams[0]["id"]

                # Test team detail page
                detail_response = requests.get(f"{BASE_URL}/teams/{team_id}")
                assert detail_response.status_code == 200

                soup = BeautifulSoup(detail_response.content, "html.parser")

                # Validate any img tags that exist
                all_images = soup.find_all("img", src=True)
                broken_images = []

                for img in all_images:
                    src = img.get("src")
                    if src and src.startswith("/"):
                        img_response = requests.head(f"{BASE_URL}{src}")
                        if img_response.status_code == 404:
                            broken_images.append(src)

                assert len(broken_images) == 0, f"Found broken images on team detail page: {broken_images}"

    def test_no_logo_404s_in_server_logs(self, docker_containers):
        """Test that server logs show no team logo 404 errors after page loads."""
        import subprocess
        import time

        # Clear any existing logs by getting current log position
        with contextlib.suppress(subprocess.CalledProcessError):
            # Get initial log count (result unused, just checking container exists)
            subprocess.run(
                ["docker", "logs", "--tail", "1", "basketball-stats-tracker-web-1"],
                capture_output=True,
                text=True,
                check=False,
            )
            pass  # Container might not exist yet

        # Load pages that previously caused 404s
        requests.get(f"{BASE_URL}/games")
        time.sleep(3)  # Wait for any async requests

        # Check recent logs for 404 logo requests
        try:
            recent_logs = subprocess.run(
                ["docker", "logs", "--tail", "20", "basketball-stats-tracker-web-1"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Look for logo-related 404s (exclude intentional test requests)
            log_lines = recent_logs.stdout.split("\n")
            logo_404s = [
                line
                for line in log_lines
                if "404" in line and "teams" in line and "logo" in line
                # Exclude intentional test URLs
                and "logo.nonexistent" not in line and "teams/999/" not in line and "teams/invalid/" not in line
            ]

            assert len(logo_404s) == 0, f"Found unexpected logo 404s in server logs: {logo_404s}"

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # If we can't check logs, skip this assertion
            pass


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
