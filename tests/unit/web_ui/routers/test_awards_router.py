"""Unit tests for the awards router."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.web_ui.api import app


class TestAwardsRouter:
    """Test cases for awards router endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_get_awards_endpoint_structure(self, client, db_session: Session):
        """Test awards endpoint returns correct structure."""
        response = client.get("/v1/awards")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "season_awards" in data
        assert "weekly_awards" in data
        assert "available_seasons" in data
        assert "total_awards" in data
        assert "award_configs" in data

        # Check that award_configs has the expected structure
        assert "weekly" in data["award_configs"]
        assert "season" in data["award_configs"]

    def test_get_awards_summary_endpoint_structure(self, client, db_session: Session):
        """Test awards summary endpoint returns correct structure."""
        response = client.get("/v1/awards/stats/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "total_awards" in data
        assert "unique_players_with_awards" in data
        assert "awards_by_type" in data
        assert "awards_by_season" in data

        # Check that counts are non-negative integers
        assert isinstance(data["total_awards"], int)
        assert data["total_awards"] >= 0
        assert isinstance(data["unique_players_with_awards"], int)
        assert data["unique_players_with_awards"] >= 0

    def test_awards_page_renders(self, client):
        """Test that the awards page renders successfully."""
        response = client.get("/awards")

        assert response.status_code == 200
        assert "Awards Showcase" in response.text
        assert "Hall of fame for season and weekly honors" in response.text

    def test_get_awards_by_season_endpoint_structure(self, client, db_session: Session):
        """Test the season-specific awards endpoint structure."""
        response = client.get("/v1/awards/2025")  # Use existing season

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "season_awards" in data
        assert "weekly_awards" in data
        assert "available_seasons" in data
        assert "total_awards" in data
