"""
Test module for database model relationships.
"""

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.data_access.models import (
    ActiveRoster,
    Game,
    GameEvent,
    GameState,
    Player,
    PlayerGameStats,
    PlayerQuarterStats,
    Team,
)


class TestModelRelationships:
    """Tests for database model relationships."""

    def test_team_player_relationship(self, db_session):
        """Test the relationship between Team and Player models."""
        # Create a team
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        # Create players for the team
        player1 = Player(
            name="Player One",
            team_id=team.id,
            jersey_number="1",
            position="PG",
            height=72,
            weight=180,
            year="Senior",
            is_active=True,
        )
        player2 = Player(
            name="Player Two",
            team_id=team.id,
            jersey_number="2",
            position="SG",
            height=75,
            weight=190,
            year="Junior",
            is_active=True,
        )

        db_session.add(player1)
        db_session.add(player2)
        db_session.commit()

        # Test forward relationship (team -> players)
        assert len(team.players) == 2
        assert player1 in team.players
        assert player2 in team.players

        # Test backward relationship (player -> team)
        assert player1.team == team
        assert player2.team == team
        assert player1.team.name == "Test Team"

    def test_game_team_relationships(self, db_session):
        """Test the relationships between Game and Team models."""
        # Create teams
        home_team = Team(name="Home Team")
        away_team = Team(name="Away Team")
        db_session.add(home_team)
        db_session.add(away_team)
        db_session.flush()

        # Create a game
        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=home_team.id,
            opponent_team_id=away_team.id,
            location="Test Arena",
        )
        db_session.add(game)
        db_session.commit()

        # Test forward relationships (game -> teams)
        assert game.playing_team == home_team
        assert game.opponent_team == away_team
        assert game.playing_team.name == "Home Team"
        assert game.opponent_team.name == "Away Team"

        # Test backward relationships (team -> games)
        assert game in home_team.home_games
        assert game in away_team.away_games
        assert len(home_team.home_games) == 1
        assert len(away_team.away_games) == 1

    def test_game_game_state_relationship(self, db_session):
        """Test the relationship between Game and GameState models."""
        # Create teams
        team1 = Team(name="Team 1")
        team2 = Team(name="Team 2")
        db_session.add(team1)
        db_session.add(team2)
        db_session.flush()

        # Create a game
        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team1.id,
            opponent_team_id=team2.id,
        )
        db_session.add(game)
        db_session.flush()

        # Create game state
        game_state = GameState(
            game_id=game.id,
            current_quarter=1,
            is_live=True,
            is_final=False,
            home_timeouts_remaining=4,
            away_timeouts_remaining=4,
        )
        db_session.add(game_state)
        db_session.commit()

        # Test forward relationship (game -> game_state)
        assert game.game_state == game_state
        assert game.game_state.current_quarter == 1
        assert game.game_state.is_live is True

        # Test backward relationship (game_state -> game)
        assert game_state.game == game
        assert game_state.game.date == date(2025, 5, 23)

    def test_player_game_stats_relationships(self, db_session):
        """Test the relationships between Player, Game, and PlayerGameStats."""
        # Create team and player
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        player = Player(
            name="Test Player",
            team_id=team.id,
            jersey_number="1",
            position="PG",
            is_active=True,
        )
        db_session.add(player)
        db_session.flush()

        # Create game
        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team.id,
            opponent_team_id=team.id,  # Self-play for test
        )
        db_session.add(game)
        db_session.flush()

        # Create player game stats
        game_stats = PlayerGameStats(
            game_id=game.id,
            player_id=player.id,
            total_2pm=5,
            total_2pa=8,
            total_3pm=2,
            total_3pa=4,
            total_ftm=3,
            total_fta=3,
            fouls=2,
        )
        db_session.add(game_stats)
        db_session.commit()

        # Test forward relationships
        assert game_stats.player == player
        assert game_stats.game == game
        assert game_stats.player.name == "Test Player"
        assert game_stats.game.date == date(2025, 5, 23)

        # Test backward relationships
        assert game_stats in player.game_stats
        assert game_stats in game.player_game_stats
        assert len(player.game_stats) == 1
        assert len(game.player_game_stats) == 1

    def test_player_quarter_stats_relationships(self, db_session):
        """Test the relationships for PlayerQuarterStats."""
        # Create necessary entities
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        player = Player(
            name="Test Player",
            team_id=team.id,
            jersey_number="1",
            position="PG",
            is_active=True,
        )
        db_session.add(player)
        db_session.flush()

        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team.id,
            opponent_team_id=team.id,
        )
        db_session.add(game)
        db_session.flush()

        game_stats = PlayerGameStats(
            game_id=game.id,
            player_id=player.id,
            total_2pm=0,
            total_2pa=0,
            total_3pm=0,
            total_3pa=0,
            total_ftm=0,
            total_fta=0,
            fouls=0,
        )
        db_session.add(game_stats)
        db_session.flush()

        # Create quarter stats for each quarter
        for quarter in range(1, 5):
            quarter_stats = PlayerQuarterStats(
                player_game_stat_id=game_stats.id,
                quarter_number=quarter,
                fg2m=1,
                fg2a=2,
                fg3m=0,
                fg3a=1,
                ftm=1,
                fta=1,
            )
            db_session.add(quarter_stats)

        db_session.commit()

        # Test forward relationship (quarter_stats -> game_stats)
        quarter_stats = db_session.query(PlayerQuarterStats).filter(PlayerQuarterStats.quarter_number == 1).first()
        assert quarter_stats.player_game_stat == game_stats
        assert quarter_stats.player_game_stat.player.name == "Test Player"

        # Test backward relationship (game_stats -> quarter_stats)
        assert len(game_stats.quarter_stats) == 4
        quarter_numbers = [qs.quarter_number for qs in game_stats.quarter_stats]
        assert sorted(quarter_numbers) == [1, 2, 3, 4]

    def test_game_event_relationships(self, db_session):
        """Test the relationships for GameEvent."""
        # Create necessary entities
        team1 = Team(name="Team 1")
        team2 = Team(name="Team 2")
        db_session.add(team1)
        db_session.add(team2)
        db_session.flush()

        player = Player(
            name="Test Player",
            team_id=team1.id,
            jersey_number="1",
            position="PG",
            is_active=True,
        )
        db_session.add(player)
        db_session.flush()

        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team1.id,
            opponent_team_id=team2.id,
        )
        db_session.add(game)
        db_session.flush()

        # Create game events
        shot_event = GameEvent(
            game_id=game.id,
            event_type="shot",
            player_id=player.id,
            team_id=team1.id,
            quarter=1,
            timestamp=datetime(2025, 5, 23, 19, 30, 0),
            details={"shot_type": "2pt", "made": True},
        )

        foul_event = GameEvent(
            game_id=game.id,
            event_type="foul",
            player_id=player.id,
            team_id=team1.id,
            quarter=1,
            timestamp=datetime(2025, 5, 23, 19, 35, 0),
            details={"foul_type": "personal"},
        )

        db_session.add(shot_event)
        db_session.add(foul_event)
        db_session.commit()

        # Test forward relationships
        assert shot_event.game == game
        assert shot_event.player == player
        assert shot_event.team == team1
        assert foul_event.game == game
        assert foul_event.player == player
        assert foul_event.team == team1

        # Test backward relationships
        assert len(game.game_events) == 2
        assert shot_event in game.game_events
        assert foul_event in game.game_events

        assert len(player.game_events) == 2
        assert shot_event in player.game_events
        assert foul_event in player.game_events

        # Note: Team doesn't have a reverse relationship to game_events

    def test_active_roster_relationships(self, db_session):
        """Test the relationships for ActiveRoster."""
        # Create necessary entities
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        player = Player(
            name="Test Player",
            team_id=team.id,
            jersey_number="1",
            position="PG",
            is_active=True,
        )
        db_session.add(player)
        db_session.flush()

        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team.id,
            opponent_team_id=team.id,
        )
        db_session.add(game)
        db_session.flush()

        # Create active roster entry
        roster_entry = ActiveRoster(
            game_id=game.id,
            player_id=player.id,
            team_id=team.id,
            is_starter=True,
            checked_in_at=datetime(2025, 5, 23, 19, 0, 0),
        )
        db_session.add(roster_entry)
        db_session.commit()

        # Test forward relationships
        assert roster_entry.game == game
        assert roster_entry.player == player
        assert roster_entry.team == team
        assert roster_entry.is_starter is True

        # Test backward relationships
        assert roster_entry in game.active_rosters
        assert roster_entry in player.active_rosters
        assert len(game.active_rosters) == 1
        assert len(player.active_rosters) == 1

    def test_cascade_deletes(self, db_session):
        """Test that cascade deletes work correctly."""
        # Create team with players
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        player = Player(
            name="Test Player",
            team_id=team.id,
            jersey_number="1",
            position="PG",
            is_active=True,
        )
        db_session.add(player)
        db_session.flush()

        # Create game with stats
        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team.id,
            opponent_team_id=team.id,
        )
        db_session.add(game)
        db_session.flush()

        game_stats = PlayerGameStats(
            game_id=game.id,
            player_id=player.id,
            total_2pm=0,
            total_2pa=0,
            total_3pm=0,
            total_3pa=0,
            total_ftm=0,
            total_fta=0,
            fouls=0,
        )
        db_session.add(game_stats)
        db_session.flush()

        quarter_stats = PlayerQuarterStats(
            player_game_stat_id=game_stats.id,
            quarter_number=1,
            fg2m=0,
            fg2a=0,
            fg3m=0,
            fg3a=0,
            ftm=0,
            fta=0,
        )
        db_session.add(quarter_stats)
        db_session.commit()

        # Verify entities exist
        assert db_session.query(Team).filter(Team.id == team.id).first() is not None
        assert db_session.query(Player).filter(Player.id == player.id).first() is not None
        assert db_session.query(Game).filter(Game.id == game.id).first() is not None
        assert db_session.query(PlayerGameStats).filter(PlayerGameStats.id == game_stats.id).first() is not None
        assert (
            db_session.query(PlayerQuarterStats).filter(PlayerQuarterStats.id == quarter_stats.id).first() is not None
        )

        # Delete game stats (should cascade to quarter stats)
        db_session.delete(game_stats)
        db_session.commit()

        # Quarter stats should be deleted due to cascade
        assert db_session.query(PlayerQuarterStats).filter(PlayerQuarterStats.id == quarter_stats.id).first() is None

        # Game, player, and team should still exist
        assert db_session.query(Game).filter(Game.id == game.id).first() is not None
        assert db_session.query(Player).filter(Player.id == player.id).first() is not None
        assert db_session.query(Team).filter(Team.id == team.id).first() is not None

    def test_unique_constraints(self, db_session):
        """Test that unique constraints work correctly."""
        # Create team
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        # Create first player with jersey number 1
        player1 = Player(
            name="Player One",
            team_id=team.id,
            jersey_number="1",
            position="PG",
            is_active=True,
        )
        db_session.add(player1)
        db_session.commit()

        # Try to create another active player with same jersey number on same team
        player2 = Player(
            name="Player Two",
            team_id=team.id,
            jersey_number="1",  # Same jersey number
            position="SG",
            is_active=True,
        )
        db_session.add(player2)

        # This should raise an integrity error due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Creating an inactive player with same jersey number should also fail
        # because the constraint is on (team_id, jersey_number) regardless of is_active
        player3 = Player(
            name="Player Three",
            team_id=team.id,
            jersey_number="1",  # Same jersey number
            position="SG",
            is_active=False,  # Inactive
        )
        db_session.add(player3)

        # This should also raise an integrity error
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # But creating a player with a different jersey number should work
        player4 = Player(
            name="Player Four",
            team_id=team.id,
            jersey_number="2",  # Different jersey number
            position="SG",
            is_active=False,  # Inactive
        )
        db_session.add(player4)
        db_session.commit()  # Should succeed

        # Verify players exist
        active_players = db_session.query(Player).filter(Player.team_id == team.id, Player.is_active.is_(True)).count()
        assert active_players == 1

        inactive_players = (
            db_session.query(Player)
            .filter(Player.team_id == team.id, Player.is_active.is_(False))
            .count()
        )
        assert inactive_players == 1

    def test_model_string_representations(self, db_session):
        """Test that model __str__ methods work correctly."""
        # Create entities
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        player = Player(
            name="Test Player",
            team_id=team.id,
            jersey_number="42",
            position="PG",
            is_active=True,
        )
        db_session.add(player)
        db_session.flush()

        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team.id,
            opponent_team_id=team.id,
        )
        db_session.add(game)
        db_session.commit()

        # Test string representations
        assert str(team) == "Test Team"
        assert "Test Player" in str(player)
        assert "#42" in str(player)
        assert str(game.date) in str(game)

    def test_model_properties_and_methods(self, db_session):
        """Test model properties and calculated methods."""
        # Create team and player
        team = Team(name="Test Team")
        db_session.add(team)
        db_session.flush()

        player = Player(
            name="Test Player",
            team_id=team.id,
            jersey_number="42",
            position="PG",
            height=75,  # 6'3"
            weight=180,
            is_active=True,
        )
        db_session.add(player)
        db_session.flush()

        # Create game and stats
        game = Game(
            date=date(2025, 5, 23),
            playing_team_id=team.id,
            opponent_team_id=team.id,
        )
        db_session.add(game)
        db_session.flush()

        game_stats = PlayerGameStats(
            game_id=game.id,
            player_id=player.id,
            total_2pm=5,
            total_2pa=10,
            total_3pm=3,
            total_3pa=6,
            total_ftm=4,
            total_fta=5,
            fouls=2,
        )
        db_session.add(game_stats)
        db_session.commit()

        # Test calculated properties if they exist
        # Note: These would need to be implemented in the models
        # This is a placeholder for future calculated properties

        # Basic property tests
        assert player.height == 75
        assert player.weight == 180
        assert player.is_active is True
        assert game_stats.total_2pm == 5
        assert game_stats.total_3pm == 3
        assert game_stats.total_ftm == 4

        # Test relationships are working
        assert game_stats.player == player
        assert game_stats.game == game
