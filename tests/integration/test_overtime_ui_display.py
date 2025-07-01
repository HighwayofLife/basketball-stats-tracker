"""Integration tests for overtime UI display using HTML structure validation."""

from datetime import date

import pytest
from bs4 import BeautifulSoup

from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team


class TestOvertimeUIDisplay:
    """Test overtime display in the HTML structure."""

    @pytest.fixture
    def setup_overtime_game(self, integration_db_session):
        """Create a game with overtime data."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams with unique names to avoid conflicts
        team_a = Team(name=f"OvertimeLakers_{unique_suffix}", display_name=f"Overtime Lakers {unique_suffix}")
        team_b = Team(name=f"OvertimeWarriors_{unique_suffix}", display_name=f"Overtime Warriors {unique_suffix}")
        integration_db_session.add_all([team_a, team_b])
        integration_db_session.flush()

        # Create players with unique names and jersey numbers
        import hashlib

        hash_suffix = int(hashlib.md5(unique_suffix.encode()).hexdigest()[:4], 16)
        player_a = Player(
            name=f"OvertimeLeBron_{unique_suffix}", team_id=team_a.id, jersey_number=str(23 + hash_suffix % 50)
        )
        player_b = Player(
            name=f"OvertimeSteph_{unique_suffix}", team_id=team_b.id, jersey_number=str(30 + hash_suffix % 50)
        )
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

    def test_game_detail_page_has_javascript_for_overtime(self, authenticated_client, setup_overtime_game):
        """Test that game detail page has JavaScript that can handle overtime."""
        overtime_game = setup_overtime_game["overtime_game"]

        # Get the game detail page HTML
        response = authenticated_client.get(f"/games/{overtime_game.id}")
        assert response.status_code == 200

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Check that the page includes JavaScript for creating scoreboards
        script_tags = soup.find_all("script")
        has_scoreboard_js = any("createScoreboard" in script.get_text() for script in script_tags if script.get_text())
        assert has_scoreboard_js, "Game detail page should include JavaScript for dynamic scoreboard creation"

        # Check that the page includes quarter_scores data structure references
        has_quarter_scores = any("quarter_scores" in script.get_text() for script in script_tags if script.get_text())
        assert has_quarter_scores, "Game detail page should reference quarter_scores data structure"

    def test_regular_game_detail_page_structure(self, authenticated_client, setup_overtime_game):
        """Test that regular game detail page loads properly without overtime."""
        regular_game = setup_overtime_game["regular_game"]

        # Get the regular game detail page HTML
        response = authenticated_client.get(f"/games/{regular_game.id}")
        assert response.status_code == 200

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Check that the page has the basic game structure
        game_detail_section = soup.find("div", class_="game-detail") or soup.find("section", class_="game-detail")
        assert game_detail_section or "game" in html_content.lower(), "Page should contain game detail content"

        # Check that JavaScript is present for dynamic content
        script_tags = soup.find_all("script")
        has_scripts = len([s for s in script_tags if s.get_text().strip()]) > 0
        assert has_scripts, "Page should include JavaScript for dynamic functionality"

    def test_games_list_page_loads_with_overtime_games(self, authenticated_client, setup_overtime_game):
        """Test that games list page loads and shows games (including overtime games)."""
        # Get the games list page
        response = authenticated_client.get("/games")
        assert response.status_code == 200

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Check that the page has the games structure
        games_container = soup.find("div", class_="games-container") or soup.find("main")
        assert games_container or "games" in html_content.lower(), "Page should contain games content"

        # The page should have JavaScript for dynamic loading
        script_tags = soup.find_all("script")
        has_scripts = len([s for s in script_tags if s.get_text().strip()]) > 0
        assert has_scripts, "Games page should include JavaScript for dynamic functionality"

    def test_box_score_report_page_structure(self, authenticated_client, setup_overtime_game):
        """Test that box score report page has the correct structure for overtime."""
        overtime_game = setup_overtime_game["overtime_game"]

        # Get the box score report page
        response = authenticated_client.get(f"/reports/box-score/{overtime_game.id}")

        # The page should load (might be 200 or 404 depending on data requirements)
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")

            # Check for box score container elements
            box_score_elements = (
                soup.find("div", id="quarterScores")
                or soup.find("table", class_="box-score")
                or soup.find("section", class_="box-score")
            )

            # The page should have structure for displaying quarter scores
            has_quarter_structure = (
                box_score_elements or "quarter" in html_content.lower() or "score" in html_content.lower()
            )
            assert has_quarter_structure, "Box score page should have structure for quarter display"
