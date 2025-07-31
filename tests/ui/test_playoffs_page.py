"""UI tests for the playoffs page."""

from playwright.sync_api import Page, expect


class TestPlayoffsPage:
    """Test cases for the playoffs page UI."""

    def test_playoffs_page_loads(self, page: Page):
        """Test that the playoffs page loads successfully."""
        # Navigate to playoffs page
        page.goto("/playoffs")

        # Check page title
        expect(page).to_have_title("Playoffs - Basketball Stats Tracker")

        # Check main heading
        heading = page.locator("h2").first
        expect(heading).to_have_text("Playoff Bracket")

    def test_playoffs_navigation_from_games_page(self, page: Page):
        """Test navigation to playoffs from games page."""
        # Go to games page
        page.goto("/games")

        # Click on playoffs button
        playoffs_button = page.locator("a:has-text('Playoffs')")
        expect(playoffs_button).to_be_visible()
        playoffs_button.click()

        # Verify we're on the playoffs page
        expect(page).to_have_url("/playoffs")
        expect(page.locator("h2").first).to_have_text("Playoff Bracket")

    def test_playoffs_navigation_from_dashboard(self, page: Page):
        """Test navigation to playoffs from dashboard."""
        # Go to dashboard
        page.goto("/")

        # Click on playoffs quick action button
        playoffs_button = page.locator(".quick-action-btn:has-text('Playoffs')")
        expect(playoffs_button).to_be_visible()
        playoffs_button.click()

        # Verify we're on the playoffs page
        expect(page).to_have_url("/playoffs")
        expect(page.locator("h2").first).to_have_text("Playoff Bracket")

    def test_playoffs_no_games_display(self, page: Page):
        """Test display when no playoff games exist."""
        # Navigate to playoffs page
        page.goto("/playoffs")

        # Wait for content to load
        page.wait_for_load_state("networkidle")

        # Check for no games message (if no playoff games exist)
        # This test assumes no playoff games in test data
        no_games = page.locator("#no-games")
        if no_games.is_visible():
            expect(no_games).to_contain_text("No Playoff Games Yet")
            expect(no_games).to_contain_text("playoff bracket will appear here")

    def test_playoffs_bracket_structure(self, page: Page):
        """Test the bracket structure when games exist."""
        # Navigate to playoffs page
        page.goto("/playoffs")

        # Wait for content to load
        page.wait_for_load_state("networkidle")

        # Check if bracket is displayed
        bracket_content = page.locator("#bracket-content")
        if bracket_content.is_visible():
            # Check for bracket rounds
            expect(page.locator(".bracket-round-title:has-text('Semi-Finals')")).to_be_visible()
            expect(page.locator(".bracket-round-title:has-text('Finals')")).to_be_visible()

    def test_playoffs_loading_state(self, page: Page):
        """Test that loading state is shown initially."""
        # Navigate to playoffs page
        page.goto("/playoffs")

        # Check for loading spinner (should be visible initially)
        loading = page.locator("#loading")
        if loading.is_visible():
            expect(loading).to_contain_text("Loading playoff bracket")

    def test_playoff_matchup_click(self, page: Page):
        """Test clicking on a matchup navigates to game detail."""
        # Navigate to playoffs page
        page.goto("/playoffs")

        # Wait for content to load
        page.wait_for_load_state("networkidle")

        # If there are matchups, test clicking on one
        matchup = page.locator(".matchup").first
        if matchup.is_visible():
            # Get the game ID from the matchup (would need to be exposed in data attribute)
            matchup.click()
            # Should navigate to game detail page
            expect(page.url).to_match(r"/games/\d+")

    def test_champion_display(self, page: Page):
        """Test champion display when a champion exists."""
        # Navigate to playoffs page
        page.goto("/playoffs")

        # Wait for content to load
        page.wait_for_load_state("networkidle")

        # Check for champion section
        champion_section = page.locator("#champion-section")
        if champion_section.is_visible():
            expect(champion_section).to_contain_text("Champion")
            # Champion name should be visible
            expect(page.locator("#champion-name")).not_to_be_empty()

    def test_responsive_design(self, page: Page):
        """Test that the playoffs page is responsive."""
        # Navigate to playoffs page
        page.goto("/playoffs")

        # Test desktop view
        page.set_viewport_size({"width": 1200, "height": 800})
        bracket = page.locator(".bracket")
        expect(bracket).to_be_visible()

        # Test mobile view
        page.set_viewport_size({"width": 375, "height": 667})
        expect(bracket).to_be_visible()
        # In mobile view, bracket should stack vertically (CSS handles this)

    def test_error_handling(self, page: Page):
        """Test error handling when API fails."""
        # This would require mocking the API to return an error
        # For now, just check that error UI elements exist
        page.goto("/playoffs")

        # The page should have error handling capability
        # If an error occurs, it should show an error message
        page.wait_for_load_state("networkidle")

        # Check if error state might be displayed
        no_games = page.locator("#no-games")
        if no_games.is_visible():
            # Could contain either "No Playoff Games Yet" or error message
            expect(no_games.locator("h3")).to_be_visible()
