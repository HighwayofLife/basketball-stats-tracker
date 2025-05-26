"""
Test module for scorebook CSV format validation.
"""

import csv
import io
from pathlib import Path

import pytest


class TestScorebookCSVFormat:
    """Tests for scorebook CSV format validation."""

    def test_valid_csv_format(self):
        """Test that our expected CSV format is valid."""
        csv_content = """Home,Blue,,,,,,
Away,Black,,,,,,
Date,5/19/2025,,,,,,
Team,Number,Player,Fouls,QT1,QT2,QT3,QT4
Black,00,Jordan,1,-/-,-/,/2,-2xxxx
Black,5,Kyle,3,-/2-/,2/,/--3,/3-
Blue,0,Jose,2,-2/-1x,-2-/-2,/2-,-2-33/33xx/2
Blue,4,Jake,2,,/,/1x,2"""

        # Parse CSV
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Validate structure
        assert len(rows) >= 5  # At least home, away, date, headers, and one player

        # Check home team row
        assert rows[0][0].lower() == "home"
        assert rows[0][1] == "Blue"

        # Check away team row
        assert rows[1][0].lower() == "away"
        assert rows[1][1] == "Black"

        # Check date row
        assert rows[2][0].lower() == "date"
        assert rows[2][1] == "5/19/2025"

        # Check headers
        headers = rows[3]
        assert headers[0] == "Team"
        assert headers[1] == "Number"
        assert headers[2] == "Player"
        assert headers[3] == "Fouls"
        assert headers[4] == "QT1"
        assert headers[5] == "QT2"
        assert headers[6] == "QT3"
        assert headers[7] == "QT4"

        # Check player data
        teams_found = set()
        for i in range(4, len(rows)):
            player_row = rows[i]
            if len(player_row) >= 3 and player_row[0] and player_row[1] and player_row[2]:
                teams_found.add(player_row[0])

        assert len(teams_found) == 2
        assert "Black" in teams_found
        assert "Blue" in teams_found

    def test_csv_without_team_names_in_header(self):
        """Test CSV where team names are only in player data."""
        csv_content = """Home,,,,,,,
Away,,,,,,,
Date,5/19/2025,,,,,,
Team,Number,Player,Fouls,QT1,QT2,QT3,QT4
Black,00,Jordan,1,-/-,-/,/2,-2xxxx
Blue,0,Jose,2,-2/-1x,-2-/-2,/2-,-2-33/33xx/2"""

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Header rows should still be present but team names may be empty
        assert rows[0][0].lower() == "home"
        assert rows[1][0].lower() in ["away", "visitor"]
        assert rows[2][0].lower() == "date"

        # Teams should be determinable from player data
        teams_found = set()
        for i in range(4, len(rows)):
            player_row = rows[i]
            if len(player_row) >= 3 and player_row[0]:
                teams_found.add(player_row[0])

        assert len(teams_found) == 2

    def test_csv_with_empty_quarters(self):
        """Test CSV with players who didn't play in some quarters."""
        csv_content = """Home,Blue,,,,,,
Away,Black,,,,,,
Date,5/19/2025,,,,,,
Team,Number,Player,Fouls,QT1,QT2,QT3,QT4
Black,11,Dan,,,,- ,
Black,24,Ethan,1,,,2,/-"""

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Check that empty quarters are handled
        dan_row = rows[4]
        assert dan_row[2] == "Dan"
        assert dan_row[4] == ""  # QT1 empty
        assert dan_row[5] == ""  # QT2 empty
        assert dan_row[6] == "- "  # QT3 has data

        ethan_row = rows[5]
        assert ethan_row[2] == "Ethan"
        assert ethan_row[4] == ""  # QT1 empty
        assert ethan_row[5] == ""  # QT2 empty
        assert ethan_row[6] == "2"  # QT3 has data
        assert ethan_row[7] == "/-"  # QT4 has data

    def test_invalid_csv_missing_required_rows(self):
        """Test CSV missing required rows should be detected."""
        csv_content = """Team,Number,Player,Fouls,QT1,QT2,QT3,QT4
Black,00,Jordan,1,-/-,-/,/2,-2xxxx"""

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Should have less than required rows
        assert len(rows) < 5

    def test_actual_import_file_format(self):
        """Test the actual import file format from the user."""
        import_file = Path(
            "/Users/highwayoflife/github/highwayoflife/basketball-stats-tracker/import/Blue-v-Black-game3-5-19-2025.csv"
        )
        if not import_file.exists():
            pytest.skip("Import file not found")

        with open(import_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Validate the actual file format
        assert len(rows) >= 5
        assert rows[0][0].lower() == "home"
        assert rows[1][0].lower() == "away"
        assert rows[2][0].lower() == "date"

        # Check headers
        headers = rows[3]
        assert "Team" in headers
        assert "Number" in headers
        assert "Player" in headers
        assert "Fouls" in headers
        assert "QT1" in headers

        # Verify teams in player data
        teams = set()
        for i in range(4, len(rows)):
            if len(rows[i]) > 0 and rows[i][0]:
                teams.add(rows[i][0])

        assert len(teams) >= 2  # Should have at least 2 teams
