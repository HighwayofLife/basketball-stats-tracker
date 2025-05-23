"""Commands for game-related operations with undo/redo support."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.data_access.crud import get_game_by_id
from app.data_access.models import Game, PlayerGameStats, PlayerQuarterStats
from app.services.commands.base import Command


class UpdateGameCommand(Command):
    """Command to update game details."""

    def __init__(self, db: Session, game_id: int, updates: dict[str, Any], description: str | None = None):
        """Initialize the update game command.

        Args:
            db: Database session
            game_id: ID of the game to update
            updates: Dictionary of fields to update
            description: Optional description
        """
        super().__init__(db, description or f"Update game {game_id}")
        self.game_id = game_id
        self.updates = updates
        self.old_values: dict[str, Any] = {}

    def execute(self) -> Game:
        """Execute the game update.

        Returns:
            Updated game object
        """
        game = get_game_by_id(self.db, self.game_id)
        if not game:
            raise ValueError(f"Game with ID {self.game_id} not found")

        # Store old values for undo
        for field, new_value in self.updates.items():
            if hasattr(game, field):
                self.old_values[field] = getattr(game, field)

                # Handle date conversion if needed
                if field == "date" and isinstance(new_value, str):
                    new_value = datetime.strptime(new_value, "%Y-%m-%d").date()

                setattr(game, field, new_value)

        # Log the update
        self.audit_service.log_update(
            entity_type="game",
            entity_id=self.game_id,
            old_values=self.old_values,
            new_values=self.updates,
            description=self.description,
        )

        self.db.flush()
        return game

    def undo(self) -> None:
        """Undo the game update."""
        game = get_game_by_id(self.db, self.game_id)
        if not game:
            raise ValueError(f"Game with ID {self.game_id} not found")

        # Restore old values
        for field, old_value in self.old_values.items():
            setattr(game, field, old_value)

        # Log the undo
        self.audit_service.log_update(
            entity_type="game",
            entity_id=self.game_id,
            old_values=self.updates,
            new_values=self.old_values,
            description=f"Undo: {self.description}",
        )

        self.db.flush()


class DeleteGameCommand(Command):
    """Command to soft delete a game."""

    def __init__(self, db: Session, game_id: int, user_id: int | None = None, description: str | None = None):
        """Initialize the delete game command.

        Args:
            db: Database session
            game_id: ID of the game to delete
            user_id: ID of user performing the delete
            description: Optional description
        """
        super().__init__(db, description or f"Delete game {game_id}")
        self.game_id = game_id
        self.user_id = user_id

    def execute(self) -> None:
        """Execute the game deletion (soft delete)."""
        game = get_game_by_id(self.db, self.game_id)
        if not game:
            raise ValueError(f"Game with ID {self.game_id} not found")

        if game.is_deleted:
            raise ValueError(f"Game {self.game_id} is already deleted")

        # Soft delete the game
        game.is_deleted = True
        game.deleted_at = datetime.utcnow()
        game.deleted_by = self.user_id

        # Log the deletion
        self.audit_service.log_delete(
            entity_type="game",
            entity_id=self.game_id,
            old_values={"is_deleted": False},
            user_id=self.user_id,
            description=self.description,
        )

        self.db.flush()

    def undo(self) -> None:
        """Undo the game deletion (restore)."""
        game = get_game_by_id(self.db, self.game_id)
        if not game:
            raise ValueError(f"Game with ID {self.game_id} not found")

        if not game.is_deleted:
            raise ValueError(f"Game {self.game_id} is not deleted")

        # Restore the game
        game.is_deleted = False
        game.deleted_at = None
        game.deleted_by = None

        # Log the restore
        self.audit_service.log_restore(
            entity_type="game",
            entity_id=self.game_id,
            restored_values={"is_deleted": False},
            user_id=self.user_id,
            description=f"Restore: {self.description}",
        )

        self.db.flush()


class UpdatePlayerGameStatsCommand(Command):
    """Command to update player game statistics."""

    def __init__(self, db: Session, player_game_stats_id: int, updates: dict[str, Any], description: str | None = None):
        """Initialize the update player game stats command.

        Args:
            db: Database session
            player_game_stats_id: ID of the player game stats to update
            updates: Dictionary of fields to update
            description: Optional description
        """
        super().__init__(db, description or f"Update player game stats {player_game_stats_id}")
        self.player_game_stats_id = player_game_stats_id
        self.updates = updates
        self.old_values: dict[str, Any] = {}

    def execute(self) -> PlayerGameStats:
        """Execute the stats update.

        Returns:
            Updated player game stats object
        """
        stats = self.db.query(PlayerGameStats).filter_by(id=self.player_game_stats_id).first()
        if not stats:
            raise ValueError(f"PlayerGameStats with ID {self.player_game_stats_id} not found")

        # Store old values for undo
        for field, new_value in self.updates.items():
            if hasattr(stats, field):
                self.old_values[field] = getattr(stats, field)
                setattr(stats, field, new_value)

        # Log the update
        self.audit_service.log_update(
            entity_type="player_game_stats",
            entity_id=self.player_game_stats_id,
            old_values=self.old_values,
            new_values=self.updates,
            description=self.description,
        )

        self.db.flush()
        return stats

    def undo(self) -> None:
        """Undo the stats update."""
        stats = self.db.query(PlayerGameStats).filter_by(id=self.player_game_stats_id).first()
        if not stats:
            raise ValueError(f"PlayerGameStats with ID {self.player_game_stats_id} not found")

        # Restore old values
        for field, old_value in self.old_values.items():
            setattr(stats, field, old_value)

        # Log the undo
        self.audit_service.log_update(
            entity_type="player_game_stats",
            entity_id=self.player_game_stats_id,
            old_values=self.updates,
            new_values=self.old_values,
            description=f"Undo: {self.description}",
        )

        self.db.flush()


class UpdatePlayerQuarterStatsCommand(Command):
    """Command to update player quarter statistics."""

    def __init__(self, db: Session, quarter_stats_id: int, updates: dict[str, Any], description: str | None = None):
        """Initialize the update player quarter stats command.

        Args:
            db: Database session
            quarter_stats_id: ID of the quarter stats to update
            updates: Dictionary of fields to update
            description: Optional description
        """
        super().__init__(db, description or f"Update quarter stats {quarter_stats_id}")
        self.quarter_stats_id = quarter_stats_id
        self.updates = updates
        self.old_values: dict[str, Any] = {}

    def execute(self) -> PlayerQuarterStats:
        """Execute the quarter stats update.

        Returns:
            Updated player quarter stats object
        """
        stats = self.db.query(PlayerQuarterStats).filter_by(id=self.quarter_stats_id).first()
        if not stats:
            raise ValueError(f"PlayerQuarterStats with ID {self.quarter_stats_id} not found")

        # Store old values for undo
        for field, new_value in self.updates.items():
            if hasattr(stats, field):
                self.old_values[field] = getattr(stats, field)
                setattr(stats, field, new_value)

        # Also update the parent game stats totals
        self._update_game_totals(stats)

        # Log the update
        self.audit_service.log_update(
            entity_type="player_quarter_stats",
            entity_id=self.quarter_stats_id,
            old_values=self.old_values,
            new_values=self.updates,
            description=self.description,
        )

        self.db.flush()
        return stats

    def undo(self) -> None:
        """Undo the quarter stats update."""
        stats = self.db.query(PlayerQuarterStats).filter_by(id=self.quarter_stats_id).first()
        if not stats:
            raise ValueError(f"PlayerQuarterStats with ID {self.quarter_stats_id} not found")

        # Restore old values
        for field, old_value in self.old_values.items():
            setattr(stats, field, old_value)

        # Update parent game stats totals
        self._update_game_totals(stats)

        # Log the undo
        self.audit_service.log_update(
            entity_type="player_quarter_stats",
            entity_id=self.quarter_stats_id,
            old_values=self.updates,
            new_values=self.old_values,
            description=f"Undo: {self.description}",
        )

        self.db.flush()

    def _update_game_totals(self, quarter_stats: PlayerQuarterStats) -> None:
        """Update the parent game stats totals based on quarter stats.

        Args:
            quarter_stats: The quarter stats that were updated
        """
        game_stats = quarter_stats.player_game_stat

        # Recalculate totals from all quarters
        total_ftm = 0
        total_fta = 0
        total_2pm = 0
        total_2pa = 0
        total_3pm = 0
        total_3pa = 0

        for qs in game_stats.quarter_stats:
            total_ftm += qs.ftm
            total_fta += qs.fta
            total_2pm += qs.fg2m
            total_2pa += qs.fg2a
            total_3pm += qs.fg3m
            total_3pa += qs.fg3a

        # Update game stats totals
        game_stats.total_ftm = total_ftm
        game_stats.total_fta = total_fta
        game_stats.total_2pm = total_2pm
        game_stats.total_2pa = total_2pa
        game_stats.total_3pm = total_3pm
        game_stats.total_3pa = total_3pa


class BatchUpdateGameStatsCommand(Command):
    """Command to update multiple player stats for a game in one transaction."""

    def __init__(
        self,
        db: Session,
        game_id: int,
        stats_updates: dict[int, dict[str, Any]],  # player_id -> updates
        description: str | None = None,
    ):
        """Initialize the batch update command.

        Args:
            db: Database session
            game_id: ID of the game
            stats_updates: Dictionary mapping player IDs to their stat updates
            description: Optional description
        """
        super().__init__(db, description or f"Batch update stats for game {game_id}")
        self.game_id = game_id
        self.stats_updates = stats_updates
        self.sub_commands: list[UpdatePlayerGameStatsCommand] = []

    def execute(self) -> list[PlayerGameStats]:
        """Execute all stats updates.

        Returns:
            List of updated player game stats
        """
        updated_stats = []

        # Get all player game stats for this game
        game_stats = self.db.query(PlayerGameStats).filter_by(game_id=self.game_id).all()
        stats_by_player = {stats.player_id: stats for stats in game_stats}

        # Create and execute sub-commands for each player update
        for player_id, updates in self.stats_updates.items():
            if player_id in stats_by_player:
                stats = stats_by_player[player_id]
                cmd = UpdatePlayerGameStatsCommand(
                    self.db, stats.id, updates, f"Update stats for player {player_id} in game {self.game_id}"
                )
                result = cmd.execute()
                updated_stats.append(result)
                self.sub_commands.append(cmd)

        return updated_stats

    def undo(self) -> None:
        """Undo all stats updates in reverse order."""
        for cmd in reversed(self.sub_commands):
            cmd.undo()
