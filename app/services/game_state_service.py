"""Service for managing live game state and events."""

from datetime import datetime
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.data_access.models import (
    ActiveRoster,
    Game,
    GameEvent,
    GameState,
    Player,
    PlayerGameStats,
    PlayerQuarterStats,
)


class GameStateService:
    """Manages the state of live basketball games."""

    def __init__(self, session: Session):
        """Initialize the game state service.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create_game(
        self,
        date: str,
        home_team_id: int,
        away_team_id: int,
        location: str | None = None,
        scheduled_time: str | None = None,
        notes: str | None = None,
    ) -> Game:
        """Create a new game.

        Args:
            date: Game date in YYYY-MM-DD format
            home_team_id: ID of the home team
            away_team_id: ID of the away team
            location: Game location (optional)
            scheduled_time: Scheduled time in HH:MM format (optional)
            notes: Additional notes (optional)

        Returns:
            Created Game object
        """
        game = Game(
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            playing_team_id=home_team_id,
            opponent_team_id=away_team_id,
            location=location,
            scheduled_time=datetime.strptime(scheduled_time, "%H:%M").time() if scheduled_time else None,
            notes=notes,
        )
        self.session.add(game)
        self.session.flush()

        # Create initial game state
        game_state = GameState(
            game_id=game.id,
            current_quarter=1,
            is_live=False,
            is_final=False,
        )
        self.session.add(game_state)
        self.session.commit()

        return game

    def start_game(self, game_id: int, home_starters: list[int], away_starters: list[int]) -> GameState:
        """Start a game and set the starting lineups.

        Args:
            game_id: ID of the game to start
            home_starters: List of player IDs for home team starters
            away_starters: List of player IDs for away team starters

        Returns:
            Updated GameState object
        """
        game = self.session.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game {game_id} not found")

        game_state = self.session.query(GameState).filter(GameState.game_id == game_id).first()
        if not game_state:
            game_state = GameState(game_id=game_id)
            self.session.add(game_state)

        if game_state.is_live:
            raise ValueError("Game is already in progress")
        if game_state.is_final:
            raise ValueError("Game has already ended")

        # Set game as live
        game_state.is_live = True
        game_state.current_quarter = 1

        # Check in starters
        self._check_in_players(game_id, game.playing_team_id, home_starters, is_starter=True)
        self._check_in_players(game_id, game.opponent_team_id, away_starters, is_starter=True)

        # Create game start event
        start_event = GameEvent(
            game_id=game_id,
            event_type="game_start",
            quarter=1,
            details={"home_starters": home_starters, "away_starters": away_starters},
        )
        self.session.add(start_event)

        self.session.commit()
        return game_state

    def record_shot(
        self,
        game_id: int,
        player_id: int,
        shot_type: str,
        made: bool,
        quarter: int | None = None,
        assisted_by: int | None = None,
    ) -> dict[str, Any]:
        """Record a shot attempt.

        Args:
            game_id: ID of the game
            player_id: ID of the player who took the shot
            shot_type: Type of shot ('2pt', '3pt', 'ft')
            made: Whether the shot was made
            quarter: Quarter number (uses current quarter if not specified)
            assisted_by: ID of player who assisted (optional)

        Returns:
            Dictionary with event details and updated stats
        """
        game_state = self._get_game_state(game_id)
        if not game_state.is_live:
            raise ValueError("Game is not in progress")

        quarter = quarter or game_state.current_quarter

        # Create shot event
        event_details = {
            "shot_type": shot_type,
            "made": made,
        }
        if assisted_by:
            event_details["assisted_by"] = assisted_by

        event = GameEvent(
            game_id=game_id,
            event_type="shot",
            player_id=player_id,
            team_id=self._get_player_team_id(player_id),
            quarter=quarter,
            details=event_details,
        )
        self.session.add(event)

        # Update player stats
        self._update_player_stats(game_id, player_id, quarter, shot_type, made)

        self.session.commit()

        return {
            "event_id": event.id,
            "player_id": player_id,
            "shot_type": shot_type,
            "made": made,
            "quarter": quarter,
        }

    def record_foul(
        self,
        game_id: int,
        player_id: int,
        foul_type: str = "personal",
        quarter: int | None = None,
    ) -> dict[str, Any]:
        """Record a foul.

        Args:
            game_id: ID of the game
            player_id: ID of the player who committed the foul
            foul_type: Type of foul ('personal', 'technical', 'flagrant')
            quarter: Quarter number (uses current quarter if not specified)

        Returns:
            Dictionary with event details and player's total fouls
        """
        game_state = self._get_game_state(game_id)
        if not game_state.is_live:
            raise ValueError("Game is not in progress")

        quarter = quarter or game_state.current_quarter

        # Create foul event
        event = GameEvent(
            game_id=game_id,
            event_type="foul",
            player_id=player_id,
            team_id=self._get_player_team_id(player_id),
            quarter=quarter,
            details={"foul_type": foul_type},
        )
        self.session.add(event)

        # Update player fouls
        player_stats = self._get_or_create_player_game_stats(game_id, player_id)
        player_stats.fouls += 1

        self.session.commit()

        return {
            "event_id": event.id,
            "player_id": player_id,
            "foul_type": foul_type,
            "quarter": quarter,
            "total_fouls": player_stats.fouls,
        }

    def substitute_players(
        self,
        game_id: int,
        team_id: int,
        players_out: list[int],
        players_in: list[int],
    ) -> dict[str, Any]:
        """Substitute players during a game.

        Args:
            game_id: ID of the game
            team_id: ID of the team making substitutions
            players_out: List of player IDs going out
            players_in: List of player IDs coming in

        Returns:
            Dictionary with substitution details
        """
        game_state = self._get_game_state(game_id)
        if not game_state.is_live:
            raise ValueError("Game is not in progress")

        # Check out players
        for player_id in players_out:
            roster_entry = (
                self.session.query(ActiveRoster)
                .filter(
                    and_(
                        ActiveRoster.game_id == game_id,
                        ActiveRoster.player_id == player_id,
                        ActiveRoster.checked_out_at.is_(None),
                    )
                )
                .first()
            )
            if roster_entry:
                roster_entry.checked_out_at = datetime.utcnow()

        # Check in players
        self._check_in_players(game_id, team_id, players_in)

        # Create substitution event
        event = GameEvent(
            game_id=game_id,
            event_type="substitution",
            team_id=team_id,
            quarter=game_state.current_quarter,
            details={"players_out": players_out, "players_in": players_in},
        )
        self.session.add(event)

        self.session.commit()

        return {
            "event_id": event.id,
            "team_id": team_id,
            "players_out": players_out,
            "players_in": players_in,
            "quarter": game_state.current_quarter,
        }

    def end_quarter(self, game_id: int) -> GameState:
        """End the current quarter.

        Args:
            game_id: ID of the game

        Returns:
            Updated GameState object
        """
        game_state = self._get_game_state(game_id)
        if not game_state.is_live:
            raise ValueError("Game is not in progress")

        if game_state.current_quarter >= 4:
            raise ValueError("Cannot advance past 4th quarter. Use finalize_game to end the game.")

        # Create quarter end event
        event = GameEvent(
            game_id=game_id,
            event_type="quarter_end",
            quarter=game_state.current_quarter,
        )
        self.session.add(event)

        # Advance to next quarter
        game_state.current_quarter += 1

        self.session.commit()
        return game_state

    def finalize_game(self, game_id: int) -> dict[str, Any]:
        """Finalize a game and calculate final scores.

        Args:
            game_id: ID of the game to finalize

        Returns:
            Dictionary with final game details and scores
        """
        game_state = self._get_game_state(game_id)
        if game_state.is_final:
            raise ValueError("Game is already finalized")

        game = self.session.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game {game_id} not found")

        # Calculate final scores
        home_score = self._calculate_team_score(game_id, game.playing_team_id)
        away_score = self._calculate_team_score(game_id, game.opponent_team_id)

        # Mark game as final
        game_state.is_live = False
        game_state.is_final = True

        # Create game end event
        event = GameEvent(
            game_id=game_id,
            event_type="game_end",
            quarter=game_state.current_quarter,
            details={"home_score": home_score, "away_score": away_score},
        )
        self.session.add(event)

        self.session.commit()

        return {
            "game_id": game_id,
            "state": "final",
            "home_team": game.playing_team.name,
            "away_team": game.opponent_team.name,
            "home_score": home_score,
            "away_score": away_score,
        }

    def get_live_game_state(self, game_id: int) -> dict[str, Any]:
        """Get the current state of a live game.

        Args:
            game_id: ID of the game

        Returns:
            Dictionary with game state, active players, and recent events
        """
        game_state = self._get_game_state(game_id)
        game = self.session.query(Game).filter(Game.id == game_id).first()

        if not game:
            raise ValueError(f"Game {game_id} not found")

        # Get active players
        active_players = self._get_active_players(game_id)

        # Get recent events
        recent_events = (
            self.session.query(GameEvent)
            .filter(GameEvent.game_id == game_id)
            .order_by(GameEvent.timestamp.desc())
            .limit(10)
            .all()
        )

        # Calculate current scores
        home_score = self._calculate_team_score(game_id, game.playing_team_id)
        away_score = self._calculate_team_score(game_id, game.opponent_team_id)

        return {
            "game_state": {
                "game_id": game_id,
                "current_quarter": game_state.current_quarter,
                "is_live": game_state.is_live,
                "is_final": game_state.is_final,
                "home_score": home_score,
                "away_score": away_score,
                "home_timeouts": game_state.home_timeouts_remaining,
                "away_timeouts": game_state.away_timeouts_remaining,
            },
            "active_players": active_players,
            "recent_events": [
                {
                    "id": event.id,
                    "type": event.event_type,
                    "player_id": event.player_id,
                    "team_id": event.team_id,
                    "quarter": event.quarter,
                    "timestamp": event.timestamp.isoformat(),
                    "details": event.details,
                }
                for event in recent_events
            ],
        }

    def undo_last_event(self, game_id: int) -> dict[str, Any]:
        """Undo the last event in a game.

        Args:
            game_id: ID of the game

        Returns:
            Dictionary with details of the undone event
        """
        # Get the last event
        last_event = (
            self.session.query(GameEvent)
            .filter(GameEvent.game_id == game_id)
            .order_by(GameEvent.timestamp.desc())
            .first()
        )

        if not last_event:
            raise ValueError("No events to undo")

        # Handle different event types
        if last_event.event_type == "shot":
            self._undo_shot(last_event)
        elif last_event.event_type == "foul":
            self._undo_foul(last_event)
        elif last_event.event_type == "substitution":
            self._undo_substitution(last_event)

        # Create undo event
        undo_event = GameEvent(
            game_id=game_id,
            event_type="undo",
            quarter=last_event.quarter,
            details={"undone_event_id": last_event.id, "undone_event_type": last_event.event_type},
        )
        self.session.add(undo_event)

        # Delete the original event
        self.session.delete(last_event)
        self.session.commit()

        return {
            "undone_event": {
                "id": last_event.id,
                "type": last_event.event_type,
                "player_id": last_event.player_id,
                "details": last_event.details,
            }
        }

    # Helper methods

    def _get_game_state(self, game_id: int) -> GameState:
        """Get the game state for a game."""
        game_state = self.session.query(GameState).filter(GameState.game_id == game_id).first()
        if not game_state:
            raise ValueError(f"Game state for game {game_id} not found")
        return game_state

    def _get_player_team_id(self, player_id: int) -> int:
        """Get the team ID for a player."""
        player = self.session.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise ValueError(f"Player {player_id} not found")
        return player.team_id

    def _check_in_players(self, game_id: int, team_id: int, player_ids: list[int], is_starter: bool = False):
        """Check in players for a game."""
        for player_id in player_ids:
            # Check if player is already checked in
            existing = (
                self.session.query(ActiveRoster)
                .filter(
                    and_(
                        ActiveRoster.game_id == game_id,
                        ActiveRoster.player_id == player_id,
                    )
                )
                .first()
            )

            if existing and existing.checked_out_at is None:
                continue  # Player is already active

            roster_entry = ActiveRoster(
                game_id=game_id,
                player_id=player_id,
                team_id=team_id,
                is_starter=is_starter,
            )
            self.session.add(roster_entry)

    def _get_or_create_player_game_stats(self, game_id: int, player_id: int) -> PlayerGameStats:
        """Get or create player game stats."""
        stats = (
            self.session.query(PlayerGameStats)
            .filter(
                and_(
                    PlayerGameStats.game_id == game_id,
                    PlayerGameStats.player_id == player_id,
                )
            )
            .first()
        )

        if not stats:
            stats = PlayerGameStats(game_id=game_id, player_id=player_id)
            self.session.add(stats)
            self.session.flush()

        return stats

    def _update_player_stats(self, game_id: int, player_id: int, quarter: int, shot_type: str, made: bool):
        """Update player statistics after a shot."""
        # Get or create game stats
        game_stats = self._get_or_create_player_game_stats(game_id, player_id)

        # Get or create quarter stats
        quarter_stats = (
            self.session.query(PlayerQuarterStats)
            .filter(
                and_(
                    PlayerQuarterStats.player_game_stat_id == game_stats.id,
                    PlayerQuarterStats.quarter_number == quarter,
                )
            )
            .first()
        )

        if not quarter_stats:
            quarter_stats = PlayerQuarterStats(
                player_game_stat_id=game_stats.id,
                quarter_number=quarter,
            )
            self.session.add(quarter_stats)

        # Update stats based on shot type
        if shot_type == "ft":
            if made:
                game_stats.total_ftm += 1
                quarter_stats.ftm += 1
            game_stats.total_fta += 1
            quarter_stats.fta += 1
        elif shot_type == "2pt":
            if made:
                game_stats.total_2pm += 1
                quarter_stats.fg2m += 1
            game_stats.total_2pa += 1
            quarter_stats.fg2a += 1
        elif shot_type == "3pt":
            if made:
                game_stats.total_3pm += 1
                quarter_stats.fg3m += 1
            game_stats.total_3pa += 1
            quarter_stats.fg3a += 1

    def _calculate_team_score(self, game_id: int, team_id: int) -> int:
        """Calculate total score for a team in a game."""
        players = self.session.query(Player).filter(Player.team_id == team_id).all()
        player_ids = [p.id for p in players]

        stats = (
            self.session.query(PlayerGameStats)
            .filter(
                and_(
                    PlayerGameStats.game_id == game_id,
                    PlayerGameStats.player_id.in_(player_ids),
                )
            )
            .all()
        )

        total_score = 0
        for stat in stats:
            total_score += stat.total_ftm
            total_score += stat.total_2pm * 2
            total_score += stat.total_3pm * 3

        return total_score

    def _get_active_players(self, game_id: int) -> dict[str, list[dict[str, Any]]]:
        """Get currently active players for both teams."""
        game = self.session.query(Game).filter(Game.id == game_id).first()
        if not game:
            return {"home": [], "away": []}

        active_rosters = (
            self.session.query(ActiveRoster, Player)
            .join(Player, ActiveRoster.player_id == Player.id)
            .filter(
                and_(
                    ActiveRoster.game_id == game_id,
                    ActiveRoster.checked_out_at.is_(None),
                )
            )
            .all()
        )

        home_players = []
        away_players = []

        for roster, player in active_rosters:
            player_info = {
                "id": player.id,
                "name": player.name,
                "jersey_number": player.jersey_number,
                "position": player.position,
                "is_starter": roster.is_starter,
            }

            if player.team_id == game.playing_team_id:
                home_players.append(player_info)
            else:
                away_players.append(player_info)

        return {"home": home_players, "away": away_players}

    def _undo_shot(self, event: GameEvent):
        """Undo a shot event."""
        if event.player_id is None:
            return  # Cannot undo a shot without a player ID

        details = event.details or {}
        shot_type = details.get("shot_type")
        made = details.get("made", False)

        # Find and update the stats
        game_stats = self._get_or_create_player_game_stats(event.game_id, event.player_id)

        quarter_stats = (
            self.session.query(PlayerQuarterStats)
            .filter(
                and_(
                    PlayerQuarterStats.player_game_stat_id == game_stats.id,
                    PlayerQuarterStats.quarter_number == event.quarter,
                )
            )
            .first()
        )

        if not quarter_stats:
            return  # Nothing to undo

        # Reverse the stats update
        if shot_type == "ft":
            if made and game_stats.total_ftm > 0:
                game_stats.total_ftm -= 1
                quarter_stats.ftm = max(0, quarter_stats.ftm - 1)
            if game_stats.total_fta > 0:
                game_stats.total_fta -= 1
                quarter_stats.fta = max(0, quarter_stats.fta - 1)
        elif shot_type == "2pt":
            if made and game_stats.total_2pm > 0:
                game_stats.total_2pm -= 1
                quarter_stats.fg2m = max(0, quarter_stats.fg2m - 1)
            if game_stats.total_2pa > 0:
                game_stats.total_2pa -= 1
                quarter_stats.fg2a = max(0, quarter_stats.fg2a - 1)
        elif shot_type == "3pt":
            if made and game_stats.total_3pm > 0:
                game_stats.total_3pm -= 1
                quarter_stats.fg3m = max(0, quarter_stats.fg3m - 1)
            if game_stats.total_3pa > 0:
                game_stats.total_3pa -= 1
                quarter_stats.fg3a = max(0, quarter_stats.fg3a - 1)

    def _undo_foul(self, event: GameEvent):
        """Undo a foul event."""
        if event.player_id is None:
            return  # Cannot undo a foul without a player ID

        game_stats = self._get_or_create_player_game_stats(event.game_id, event.player_id)
        if game_stats.fouls > 0:
            game_stats.fouls -= 1

    def _undo_substitution(self, event: GameEvent):
        """Undo a substitution event."""
        details = event.details or {}
        players_out = details.get("players_out", [])
        players_in = details.get("players_in", [])

        # Reverse the substitution
        # Check out the players that came in
        for player_id in players_in:
            roster_entry = (
                self.session.query(ActiveRoster)
                .filter(
                    and_(
                        ActiveRoster.game_id == event.game_id,
                        ActiveRoster.player_id == player_id,
                        ActiveRoster.checked_out_at.is_(None),
                    )
                )
                .first()
            )
            if roster_entry:
                roster_entry.checked_out_at = datetime.utcnow()

        # Check back in the players that went out
        for player_id in players_out:
            roster_entry = (
                self.session.query(ActiveRoster)
                .filter(
                    and_(
                        ActiveRoster.game_id == event.game_id,
                        ActiveRoster.player_id == player_id,
                    )
                )
                .order_by(ActiveRoster.checked_in_at.desc())
                .first()
            )
            if roster_entry and roster_entry.checked_out_at is not None:
                roster_entry.checked_out_at = None
