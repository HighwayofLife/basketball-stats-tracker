"""
Unit tests for admin authentication requirements.
"""


class TestAdminAuthentication:
    """Test cases for admin authentication requirements using shared fixtures."""

    def test_admin_can_access_seasons(self, authenticated_client):
        """Test that admin users can access seasons endpoints."""
        # Get seasons
        response = authenticated_client.get("/v1/seasons")
        assert response.status_code == 200
        assert "seasons" in response.json()

    def test_non_admin_cannot_access_seasons(self, non_admin_client):
        """Test that non-admin users cannot access seasons endpoints."""
        # Get seasons - should fail
        response = non_admin_client.get("/v1/seasons")
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_unauthenticated_cannot_access_seasons(self, unit_unauthenticated_client):
        """Test that unauthenticated users cannot access seasons endpoints."""
        # Get seasons - should fail with 401
        response = unit_unauthenticated_client.get("/v1/seasons")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_non_admin_cannot_create_season(self, non_admin_client):
        """Test that non-admin users cannot create seasons."""
        season_data = {
            "name": "Test Season",
            "code": "TEST2025",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        }

        response = non_admin_client.post("/v1/seasons", json=season_data)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_non_admin_cannot_update_season(self, non_admin_client):
        """Test that non-admin users cannot update seasons."""
        update_data = {"name": "Updated Season"}
        response = non_admin_client.put("/v1/seasons/1", json=update_data)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_non_admin_cannot_activate_season(self, non_admin_client):
        """Test that non-admin users cannot activate seasons."""
        response = non_admin_client.post("/v1/seasons/1/activate")
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_non_admin_cannot_delete_season(self, non_admin_client):
        """Test that non-admin users cannot delete seasons."""
        response = non_admin_client.delete("/v1/seasons/1")
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_admin_seasons_page_loads_for_all_users(self, non_admin_client):
        """Test that the admin seasons HTML page loads (auth is handled client-side)."""
        response = non_admin_client.get("/admin/seasons")
        assert response.status_code == 200
        # The page loads but client-side JS will redirect if no admin token
        assert "Season Management" in response.text
