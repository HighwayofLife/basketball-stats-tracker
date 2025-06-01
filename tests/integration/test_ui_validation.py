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

import logging
import subprocess
import time

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
                    logger.info("Web service is ready")
                    return
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
                assert f"/v1/players/${player_id}/stats" in content.replace("{playerId}", str(player_id)), (
                    "Player detail page should use /v1/players/ID/stats endpoint"
                )
                assert f"/v1/players/${player_id}/upload-image" in content.replace("{playerId}", str(player_id)), (
                    "Player detail page should use /v1/players/ID/upload-image endpoint"
                )

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
        expected_paths = ["/players", "/teams", "/games", "/reports"]
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
                assert "application/json" in response.headers.get("content-type", ""), (
                    f"API endpoint {endpoint} not returning JSON"
                )


def test_container_health_check():
    """Test that containers can be started and stopped independently."""
    manager = DockerContainerManager()

    try:
        manager.start_containers()

        # Verify containers are running
        result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"], capture_output=True, text=True
        )

        running_services = result.stdout.strip().split("\n") if result.stdout.strip() else []
        assert "web" in running_services, "Web service not running"
        assert "database" in running_services, "Database service not running"

    finally:
        manager.stop_containers()

        # Verify containers are stopped
        result = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"], capture_output=True, text=True
        )

        running_services = result.stdout.strip().split("\n") if result.stdout.strip() else []
        assert "web" not in running_services, "Web service still running after stop"
        assert "database" not in running_services, "Database service still running after stop"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
