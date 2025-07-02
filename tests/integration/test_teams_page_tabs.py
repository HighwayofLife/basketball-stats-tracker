"""Integration tests for teams page tab functionality."""


class TestTeamsPageTabs:
    """Integration tests for teams page tab navigation and URL parameters."""

    def test_teams_page_default_tab(self, authenticated_client):
        """Test that teams page loads with default teams tab active."""
        response = authenticated_client.get("/teams")

        assert response.status_code == 200
        content = response.text

        # Check that teams tab is active by default
        assert 'button class="tab-button active"' in content
        assert "onclick=\"switchTab('teams')\"" in content

        # Check that teams content div has active class
        assert 'id="teams-tab" class="tab-content active"' in content

        # Check that rankings tab is not active
        assert 'id="rankings-tab" class="tab-content active"' not in content

    def test_teams_page_rankings_tab_via_url_param(self, authenticated_client):
        """Test that ?tab=rankings parameter activates rankings tab."""
        response = authenticated_client.get("/teams?tab=rankings")

        assert response.status_code == 200
        content = response.text

        # Check that rankings tab is active
        assert "onclick=\"switchTab('rankings')\"" in content

        # Check that rankings content div has active class
        assert 'id="rankings-tab" class="tab-content active"' in content

        # Check that teams tab is not active
        assert 'id="teams-tab" class="tab-content active"' not in content

        # Check that JavaScript will load rankings data
        assert "const activeTab = 'rankings'" in content
        assert "if (activeTab === 'rankings')" in content
        assert "loadTeamRankings()" in content

    def test_teams_page_invalid_tab_param_defaults_to_teams(self, authenticated_client):
        """Test that invalid tab parameter defaults to teams tab."""
        response = authenticated_client.get("/teams?tab=invalid")

        assert response.status_code == 200
        content = response.text

        # Check that teams tab is active (fallback)
        assert 'id="teams-tab" class="tab-content active"' in content

        # Check that rankings tab is not active
        assert 'id="rankings-tab" class="tab-content active"' not in content

        # Check JavaScript active tab variable - backend should sanitize invalid values to 'teams'
        assert "const activeTab = 'teams'" in content

    def test_teams_page_case_sensitive_tab_param(self, authenticated_client):
        """Test that tab parameter is case sensitive."""
        response = authenticated_client.get("/teams?tab=Rankings")

        assert response.status_code == 200
        content = response.text

        # With case mismatch, should not activate rankings tab
        assert 'id="teams-tab" class="tab-content active"' in content
        assert 'id="rankings-tab" class="tab-content active"' not in content

        # Check JavaScript gets sanitized value (invalid case becomes 'teams')
        assert "const activeTab = 'teams'" in content

    def test_teams_page_tab_navigation_elements(self, authenticated_client):
        """Test that all required tab navigation elements are present."""
        response = authenticated_client.get("/teams")

        assert response.status_code == 200
        content = response.text

        # Check for tab navigation container
        assert 'class="tab-navigation"' in content

        # Check for both tab buttons
        assert "onclick=\"switchTab('teams')\"" in content
        assert "onclick=\"switchTab('rankings')\"" in content

        # Check for both content divs
        assert 'id="teams-tab"' in content
        assert 'id="rankings-tab"' in content

        # Check for JavaScript function
        assert "function switchTab(tabName)" in content

    def test_teams_page_rankings_tab_functionality(self, authenticated_client):
        """Test that rankings tab loads team rankings data."""
        response = authenticated_client.get("/teams?tab=rankings")

        assert response.status_code == 200
        content = response.text

        # Check for rankings table structure
        assert 'id="team-rankings-table"' in content
        assert "sortable-table" in content

        # Check for rankings table headers
        expected_headers = [
            "Team",
            "Games",
            "Avg PPG",
            "FG%",
            "Opp PPG",
            "Opp FG%",
            "Offensive Rating",
            "Defensive Rating",
            "Point Diff",
        ]

        for header in expected_headers:
            assert header in content

        # Check for JavaScript function to load rankings
        assert "function loadTeamRankings()" in content
        assert "/v1/teams/rankings" in content

    def test_teams_page_multiple_query_params(self, authenticated_client):
        """Test that tab parameter works with other query parameters."""
        response = authenticated_client.get("/teams?tab=rankings&other=value")

        assert response.status_code == 200
        content = response.text

        # Rankings tab should still be active
        assert 'id="rankings-tab" class="tab-content active"' in content
        assert "const activeTab = 'rankings'" in content

    def test_teams_page_empty_tab_param(self, authenticated_client):
        """Test that empty tab parameter defaults to teams tab."""
        response = authenticated_client.get("/teams?tab=")

        assert response.status_code == 200
        content = response.text

        # Should default to teams tab
        assert 'id="teams-tab" class="tab-content active"' in content
        assert 'id="rankings-tab" class="tab-content active"' not in content

        # Empty tab should be sanitized to 'teams'
        assert "const activeTab = 'teams'" in content

    def test_teams_page_authentication_context(self, unauthenticated_client):
        """Test that teams page works for unauthenticated users."""
        response = unauthenticated_client.get("/teams?tab=rankings")

        assert response.status_code == 200
        content = response.text

        # Rankings tab should still work for unauthenticated users
        assert 'id="rankings-tab" class="tab-content active"' in content
        assert "const activeTab = 'rankings'" in content

    def test_teams_page_url_update_javascript(self, authenticated_client):
        """Test that JavaScript functions for URL updates are present."""
        response = authenticated_client.get("/teams")

        assert response.status_code == 200
        content = response.text

        # Check for URL update functionality
        assert "function updateUrlParameter(paramName, paramValue)" in content
        assert "window.history.pushState" in content
        assert "updateUrlParameter('tab', tabName)" in content

        # Check for browser history handling
        assert "function handlePopState(event)" in content
        assert "function switchTabWithoutHistory(tabName)" in content
        assert "window.addEventListener('popstate', handlePopState)" in content
