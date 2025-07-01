"""Functional tests for overtime UI display."""

from datetime import date

import pytest
from playwright.sync_api import Page, expect

from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team


class TestOvertimeUIDisplay:
    """Test overtime display in the UI."""

    @pytest.fixture
    def setup_overtime_game(self, integration_db_session):
        """Create a game with overtime data."""
        # Create teams
        team_a = Team(name="Lakers", display_name="Los Angeles Lakers")
        team_b = Team(name="Warriors", display_name="Golden State Warriors")
        integration_db_session.add_all([team_a, team_b])
        integration_db_session.flush()

        # Create players
        player_a = Player(name="LeBron James", team_id=team_a.id, jersey_number="23")
        player_b = Player(name="Stephen Curry", team_id=team_b.id, jersey_number="30")
        integration_db_session.add_all([player_a, player_b])
        integration_db_session.flush()

        # Create overtime game
        overtime_game = Game(
            date=date(2025, 7, 1),
            playing_team_id=team_a.id,
            opponent_team_id=team_b.id,
        )
        integration_db_session.add(overtime_game)
        integration_db_session.flush()

        # Add stats with overtime
        for player in [player_a, player_b]:
            pgs = PlayerGameStats(
                game_id=overtime_game.id,
                player_id=player.id,
                fouls=3,
                total_ftm=10,
                total_fta=12,
                total_2pm=8,
                total_2pa=15,
                total_3pm=3,
                total_3pa=8,
            )
            integration_db_session.add(pgs)
            integration_db_session.flush()

            # Add quarter stats including OT1 and OT2
            for quarter in range(1, 7):
                pqs = PlayerQuarterStats(
                    player_game_stat_id=pgs.id,
                    quarter_number=quarter,
                    ftm=2 if quarter <= 4 else 1,
                    fta=2,
                    fg2m=2 if quarter <= 4 else 0,
                    fg2a=3 if quarter <= 4 else 1,
                    fg3m=0 if quarter != 2 else 1,
                    fg3a=1 if quarter in [2, 3] else 0,
                )
                integration_db_session.add(pqs)

        # Create regular game (no overtime)
        regular_game = Game(
            date=date(2025, 7, 2),
            playing_team_id=team_a.id,
            opponent_team_id=team_b.id,
        )
        integration_db_session.add(regular_game)
        integration_db_session.flush()

        # Add stats without overtime
        for player in [player_a, player_b]:
            pgs = PlayerGameStats(
                game_id=regular_game.id,
                player_id=player.id,
                fouls=2,
                total_ftm=8,
                total_fta=10,
                total_2pm=7,
                total_2pa=12,
                total_3pm=2,
                total_3pa=6,
            )
            integration_db_session.add(pgs)
            integration_db_session.flush()

            # Add quarter stats for regular 4 quarters only
            for quarter in range(1, 5):
                pqs = PlayerQuarterStats(
                    player_game_stat_id=pgs.id,
                    quarter_number=quarter,
                    ftm=2,
                    fta=2,
                    fg2m=1 if quarter <= 2 else 2,
                    fg2a=2 if quarter <= 2 else 3,
                    fg3m=0 if quarter != 3 else 1,
                    fg3a=1 if quarter == 3 else 0,
                )
                integration_db_session.add(pqs)

        integration_db_session.commit()

        return {
            "team_a": team_a,
            "team_b": team_b,
            "overtime_game": overtime_game,
            "regular_game": regular_game,
        }

    def test_overtime_game_shows_ot_columns(self, page: Page, base_url: str, setup_overtime_game):
        """Test that games with overtime display OT1 and OT2 columns."""
        overtime_game = setup_overtime_game["overtime_game"]

        # Navigate to game detail page
        page.goto(f"{base_url}/games/{overtime_game.id}")

        # Wait for scoreboard to load
        page.wait_for_selector(".quarter-scores-table", timeout=10000)

        # Check that OT columns are present
        ot1_headers = page.locator("th:has-text('OT1')")
        ot2_headers = page.locator("th:has-text('OT2')")

        expect(ot1_headers).to_have_count(1)
        expect(ot2_headers).to_have_count(1)

        # Verify all quarter headers are present in correct order
        headers = page.locator(".quarter-scores-table th").all_text_contents()
        expected_headers = ["Team", "Q1", "Q2", "Q3", "Q4", "OT1", "OT2", "Total"]

        # Filter to just the header row
        header_row = [h for h in headers if h in expected_headers or h in ["Lakers", "Warriors"]][:8]
        assert header_row == expected_headers

        # Verify OT scores are displayed
        # Find score cells in the table
        score_cells = page.locator(".quarter-scores-table td").all_text_contents()

        # Should have scores for all quarters including OT
        assert len([s for s in score_cells if s.isdigit()]) >= 12  # 6 quarters x 2 teams minimum

    def test_regular_game_no_ot_columns(self, page: Page, base_url: str, setup_overtime_game):
        """Test that games without overtime do not display OT columns."""
        regular_game = setup_overtime_game["regular_game"]

        # Navigate to game detail page
        page.goto(f"{base_url}/games/{regular_game.id}")

        # Wait for scoreboard to load
        page.wait_for_selector(".quarter-scores-table", timeout=10000)

        # Check that OT columns are NOT present
        ot1_headers = page.locator("th:has-text('OT1')")
        ot2_headers = page.locator("th:has-text('OT2')")

        expect(ot1_headers).to_have_count(0)
        expect(ot2_headers).to_have_count(0)

        # Verify only regular quarter headers are present
        headers = page.locator(".quarter-scores-table th").all_text_contents()
        expected_headers = ["Team", "Q1", "Q2", "Q3", "Q4", "Total"]

        # Filter to just the header row
        header_row = [h for h in headers if h in expected_headers or h in ["Lakers", "Warriors"]][:6]
        assert header_row == expected_headers

    def test_box_score_overtime_display(self, page: Page, base_url: str, setup_overtime_game):
        """Test that box score report correctly displays overtime."""
        overtime_game = setup_overtime_game["overtime_game"]

        # Navigate to box score report
        page.goto(f"{base_url}/reports/box-score/{overtime_game.id}")

        # Wait for the box score to load
        page.wait_for_selector("#quarterScores", timeout=10000)

        # Check quarter headers
        quarter_headers = page.locator("#quarter-headers-container th").all_text_contents()

        # Should include OT1 and OT2
        assert "OT1" in quarter_headers
        assert "OT2" in quarter_headers

        # Verify the quarter scores table has correct number of columns
        score_rows = page.locator("#quarterScores tr")
        expect(score_rows).to_have_count(2)  # Two teams

        # Each row should have 8 cells: Team + 6 quarters + Total
        first_row_cells = score_rows.nth(0).locator("td")
        expect(first_row_cells).to_have_count(8)

    def test_games_list_overtime_indicator(self, page: Page, base_url: str, setup_overtime_game):
        """Test that games list shows some indicator for overtime games."""
        # Navigate to games list
        page.goto(f"{base_url}/games")

        # Wait for games list to load
        page.wait_for_selector(".games-container", timeout=10000)

        # The games list might show final scores that indicate overtime
        # This is optional - the key test is that the detail page shows OT correctly

        # At minimum, both games should be listed
        game_cards = page.locator(".game-card")
        expect(game_cards).to_have_count(2)

    def test_responsive_overtime_display(self, page: Page, base_url: str, setup_overtime_game):
        """Test that overtime display works on mobile viewport."""
        overtime_game = setup_overtime_game["overtime_game"]

        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})

        # Navigate to game detail page
        page.goto(f"{base_url}/games/{overtime_game.id}")

        # Wait for scoreboard to load
        page.wait_for_selector(".quarter-scores-table", timeout=10000)

        # On mobile, the table should still show OT columns
        # Check data-label attributes which are used for responsive display
        ot1_cells = page.locator("td[data-label='OT1']")
        ot2_cells = page.locator("td[data-label='OT2']")

        # Should have OT cells for both teams
        expect(ot1_cells.first).to_be_visible()
        expect(ot2_cells.first).to_be_visible()
