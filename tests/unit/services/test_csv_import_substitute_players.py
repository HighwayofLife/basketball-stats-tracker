"""Tests for CSV import of substitute players."""

import csv
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.data_access.models import Player, Team
from app.services.import_services.csv_parser import CSVParser
from app.services.import_services.import_processor import ImportProcessor


class TestSubstitutePlayerCSVImport:
    """Test cases for importing substitute players via CSV."""

    def test_csv_parser_reads_is_substitute_column(self):
        """Test that CSV parser correctly reads the is_substitute column."""
        # Create a temporary CSV file with substitute players
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['team_name', 'player_name', 'jersey_number', 'is_substitute'])
            writer.writerow(['Warriors', 'Regular Player', '23', ''])
            writer.writerow(['Warriors', 'Sub Player 1', '1', 'true'])
            writer.writerow(['Lakers', 'Sub Player 2', '0', 'yes'])
            writer.writerow(['Lakers', 'Sub Player 3', '00', 'Y'])
            writer.writerow(['Celtics', 'Regular Player 2', '15', 'false'])
            writer.writerow(['Celtics', 'Sub Player 4', '99', '1'])
            writer.writerow(['Heat', 'Sub Player 5', '88', 'x'])
            f.flush()
            
            # Parse the CSV
            team_data, player_data = CSVParser.read_roster_csv(Path(f.name))
            
        # Verify team data
        assert len(team_data) == 4  # 4 unique teams
        
        # Verify player data
        assert len(player_data) == 7
        
        # Check regular players
        regular_players = [p for p in player_data if not p.get('is_substitute', False)]
        assert len(regular_players) == 2
        assert regular_players[0]['name'] == 'Regular Player'
        assert regular_players[1]['name'] == 'Regular Player 2'
        
        # Check substitute players
        substitute_players = [p for p in player_data if p.get('is_substitute', False)]
        assert len(substitute_players) == 5
        substitute_names = [p['name'] for p in substitute_players]
        assert 'Sub Player 1' in substitute_names
        assert 'Sub Player 2' in substitute_names
        assert 'Sub Player 3' in substitute_names
        assert 'Sub Player 4' in substitute_names
        assert 'Sub Player 5' in substitute_names

    def test_import_processor_creates_substitute_players(self, db_session):
        """Test that import processor correctly creates substitute players."""
        # Create teams
        warriors = Team(name="Warriors")
        guest_team = Team(name="Guest Players")
        db_session.add_all([warriors, guest_team])
        db_session.commit()
        
        # Create import processor
        processor = ImportProcessor(db_session)
        
        # Process players including substitutes
        player_data = [
            {
                'team_name': 'Warriors',
                'name': 'Regular Player',
                'jersey_number': '23',
                'is_substitute': False
            },
            {
                'team_name': 'Warriors',
                'name': 'Sub Player 1',
                'jersey_number': '1',
                'is_substitute': True
            },
            {
                'team_name': 'Any Team',  # Team name doesn't matter for substitutes
                'name': 'Sub Player 2',
                'jersey_number': '0',
                'is_substitute': True
            }
        ]
        
        players_processed, players_error = processor.process_players(player_data)
        
        # Verify results
        assert players_processed == 3
        assert players_error == 0
        
        # Check regular player
        regular = db_session.query(Player).filter_by(name='Regular Player').first()
        assert regular is not None
        assert regular.team_id == warriors.id
        assert regular.is_substitute is False
        
        # Check substitute players
        sub1 = db_session.query(Player).filter_by(name='Sub Player 1').first()
        assert sub1 is not None
        assert sub1.team_id == guest_team.id
        assert sub1.is_substitute is True
        assert sub1.jersey_number == '1'
        
        sub2 = db_session.query(Player).filter_by(name='Sub Player 2').first()
        assert sub2 is not None
        assert sub2.team_id == guest_team.id
        assert sub2.is_substitute is True
        assert sub2.jersey_number == '0'

    def test_import_processor_handles_duplicate_substitute(self, db_session):
        """Test that import processor handles duplicate substitute players correctly."""
        # Create Guest Players team
        guest_team = Team(name="Guest Players")
        db_session.add(guest_team)
        db_session.commit()
        
        # Create existing substitute
        existing_sub = Player(
            name="Sub Player",
            jersey_number="1",
            team_id=guest_team.id,
            is_substitute=True
        )
        db_session.add(existing_sub)
        db_session.commit()
        
        # Create import processor
        processor = ImportProcessor(db_session)
        
        # Try to import the same substitute
        player_data = [
            {
                'team_name': 'Any Team',
                'name': 'Sub Player',
                'jersey_number': '1',
                'is_substitute': True
            }
        ]
        
        players_processed, players_error = processor.process_players(player_data)
        
        # Should process successfully (no duplicate created)
        assert players_processed == 1
        assert players_error == 0
        
        # Verify only one substitute exists
        subs = db_session.query(Player).filter_by(
            name='Sub Player',
            jersey_number='1',
            is_substitute=True
        ).all()
        assert len(subs) == 1

    def test_csv_import_with_optional_fields(self):
        """Test CSV import with all optional fields for substitute players."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow([
                'team_name', 'player_name', 'jersey_number', 'position', 
                'height', 'weight', 'year', 'is_substitute'
            ])
            writer.writerow([
                'Warriors', 'Complete Sub', '99', 'SF', '78', '210', 'Senior', 'true'
            ])
            f.flush()
            
            # Parse the CSV
            team_data, player_data = CSVParser.read_roster_csv(Path(f.name))
            
        assert len(player_data) == 1
        player = player_data[0]
        assert player['name'] == 'Complete Sub'
        assert player['jersey_number'] == '99'
        assert player['position'] == 'SF'
        assert player['height'] == '78'
        assert player['weight'] == '210'
        assert player['year'] == 'Senior'
        assert player['is_substitute'] is True

    @patch('typer.echo')
    def test_import_processor_logs_substitute_creation(self, mock_echo, db_session):
        """Test that import processor logs when creating substitute players."""
        # Create Guest Players team
        guest_team = Team(name="Guest Players")
        db_session.add(guest_team)
        db_session.commit()
        
        # Create import processor
        processor = ImportProcessor(db_session)
        
        # Process a substitute player
        player_data = [
            {
                'team_name': 'Any',
                'name': 'New Sub',
                'jersey_number': '7',
                'is_substitute': True
            }
        ]
        
        processor.process_players(player_data)
        
        # Verify log message
        mock_echo.assert_any_call("Created substitute player: New Sub #7")

    def test_csv_parser_handles_missing_is_substitute_column(self):
        """Test that CSV parser handles files without is_substitute column."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['team_name', 'player_name', 'jersey_number'])
            writer.writerow(['Warriors', 'Regular Player', '23'])
            f.flush()
            
            # Parse the CSV
            team_data, player_data = CSVParser.read_roster_csv(Path(f.name))
            
        assert len(player_data) == 1
        player = player_data[0]
        assert 'is_substitute' not in player  # Column not present
        assert player['name'] == 'Regular Player'