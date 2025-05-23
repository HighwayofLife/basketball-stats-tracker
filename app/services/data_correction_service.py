"""Service for data corrections with undo/redo functionality."""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.services.commands import (
    BatchUpdateGameStatsCommand,
    ChangeJerseyNumberCommand,
    CommandHistory,
    DeleteGameCommand,
    DeletePlayerCommand,
    DeleteTeamCommand,
    RenameTeamCommand,
    TransferPlayerCommand,
    UpdateGameCommand,
    UpdatePlayerCommand,
    UpdatePlayerGameStatsCommand,
    UpdatePlayerQuarterStatsCommand,
    UpdateTeamCommand,
)


class DataCorrectionService:
    """Service for managing data corrections with full undo/redo support."""

    def __init__(self, db: Session):
        """Initialize the data correction service.

        Args:
            db: Database session
        """
        self.db = db
        self.history = CommandHistory(max_history=100)

    # Team operations
    def update_team(self, team_id: int, updates: dict[str, Any]) -> Any:
        """Update team details.

        Args:
            team_id: ID of the team to update
            updates: Dictionary of fields to update

        Returns:
            Updated team object
        """
        cmd = UpdateTeamCommand(self.db, team_id, updates)
        return self.history.execute(cmd)

    def rename_team(self, team_id: int, new_name: str) -> Any:
        """Rename a team.

        Args:
            team_id: ID of the team to rename
            new_name: New team name

        Returns:
            Updated team object
        """
        cmd = RenameTeamCommand(self.db, team_id, new_name)
        return self.history.execute(cmd)

    def delete_team(self, team_id: int, user_id: int | None = None) -> None:
        """Soft delete a team.

        Args:
            team_id: ID of the team to delete
            user_id: ID of user performing the deletion
        """
        cmd = DeleteTeamCommand(self.db, team_id, user_id)
        self.history.execute(cmd)

    # Player operations
    def update_player(self, player_id: int, updates: dict[str, Any]) -> Any:
        """Update player details.

        Args:
            player_id: ID of the player to update
            updates: Dictionary of fields to update

        Returns:
            Updated player object
        """
        cmd = UpdatePlayerCommand(self.db, player_id, updates)
        return self.history.execute(cmd)

    def change_jersey_number(self, player_id: int, new_jersey_number: int) -> Any:
        """Change a player's jersey number.

        Args:
            player_id: ID of the player
            new_jersey_number: New jersey number

        Returns:
            Updated player object
        """
        cmd = ChangeJerseyNumberCommand(self.db, player_id, new_jersey_number)
        return self.history.execute(cmd)

    def transfer_player(self, player_id: int, new_team_id: int) -> Any:
        """Transfer a player to a different team.

        Args:
            player_id: ID of the player
            new_team_id: ID of the new team

        Returns:
            Updated player object
        """
        cmd = TransferPlayerCommand(self.db, player_id, new_team_id)
        return self.history.execute(cmd)

    def delete_player(self, player_id: int, user_id: int | None = None) -> None:
        """Soft delete a player.

        Args:
            player_id: ID of the player to delete
            user_id: ID of user performing the deletion
        """
        cmd = DeletePlayerCommand(self.db, player_id, user_id)
        self.history.execute(cmd)

    # Game operations
    def update_game(self, game_id: int, updates: dict[str, Any]) -> Any:
        """Update game details.

        Args:
            game_id: ID of the game to update
            updates: Dictionary of fields to update

        Returns:
            Updated game object
        """
        cmd = UpdateGameCommand(self.db, game_id, updates)
        return self.history.execute(cmd)

    def delete_game(self, game_id: int, user_id: int | None = None) -> None:
        """Soft delete a game.

        Args:
            game_id: ID of the game to delete
            user_id: ID of user performing the deletion
        """
        cmd = DeleteGameCommand(self.db, game_id, user_id)
        self.history.execute(cmd)

    # Game stats operations
    def update_player_game_stats(self, player_game_stats_id: int, updates: dict[str, Any]) -> Any:
        """Update player game statistics.

        Args:
            player_game_stats_id: ID of the player game stats
            updates: Dictionary of fields to update

        Returns:
            Updated stats object
        """
        cmd = UpdatePlayerGameStatsCommand(self.db, player_game_stats_id, updates)
        return self.history.execute(cmd)

    def update_player_quarter_stats(self, quarter_stats_id: int, updates: dict[str, Any]) -> Any:
        """Update player quarter statistics.

        Args:
            quarter_stats_id: ID of the quarter stats
            updates: Dictionary of fields to update

        Returns:
            Updated stats object
        """
        cmd = UpdatePlayerQuarterStatsCommand(self.db, quarter_stats_id, updates)
        return self.history.execute(cmd)

    def batch_update_game_stats(self, game_id: int, stats_updates: dict[int, dict[str, Any]]) -> list[Any]:
        """Update multiple player stats for a game.

        Args:
            game_id: ID of the game
            stats_updates: Dictionary mapping player IDs to their stat updates

        Returns:
            List of updated stats objects
        """
        cmd = BatchUpdateGameStatsCommand(self.db, game_id, stats_updates)
        return self.history.execute(cmd)

    # Undo/Redo operations
    def undo(self) -> bool:
        """Undo the last operation.

        Returns:
            True if an operation was undone, False otherwise
        """
        return self.history.undo()

    def redo(self) -> bool:
        """Redo the last undone operation.

        Returns:
            True if an operation was redone, False otherwise
        """
        return self.history.redo()

    def can_undo(self) -> bool:
        """Check if undo is available.

        Returns:
            True if there are operations to undo
        """
        return self.history.can_undo()

    def can_redo(self) -> bool:
        """Check if redo is available.

        Returns:
            True if there are operations to redo
        """
        return self.history.can_redo()

    def get_history(self) -> list[dict[str, Any]]:
        """Get the command history.

        Returns:
            List of command summaries
        """
        return self.history.get_history()

    def clear_history(self) -> None:
        """Clear all command history."""
        self.history.clear()

    # Bulk restore operations
    def restore_deleted_items(
        self, entity_type: str, start_date: date | None = None, end_date: date | None = None
    ) -> int:
        """Restore soft-deleted items of a specific type.

        Args:
            entity_type: Type of entity to restore ('team', 'player', 'game')
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Number of items restored
        """
        count = 0

        if entity_type == "team":
            from app.data_access.models import Team

            query = self.db.query(Team).filter(Team.is_deleted)
            if start_date and end_date:
                query = query.filter(Team.deleted_at >= start_date, Team.deleted_at <= end_date)

            teams = query.all()
            for team in teams:
                team.is_deleted = False
                team.deleted_at = None
                team.deleted_by = None
                count += 1

        elif entity_type == "player":
            from app.data_access.models import Player

            player_query = self.db.query(Player).filter(Player.is_deleted)
            if start_date and end_date:
                player_query = player_query.filter(Player.deleted_at >= start_date, Player.deleted_at <= end_date)

            players = player_query.all()
            for player in players:
                player.is_deleted = False
                player.deleted_at = None
                player.deleted_by = None
                player.is_active = True
                count += 1

        elif entity_type == "game":
            from app.data_access.models import Game

            game_query = self.db.query(Game).filter(Game.is_deleted)
            if start_date and end_date:
                game_query = game_query.filter(Game.deleted_at >= start_date, Game.deleted_at <= end_date)

            games = game_query.all()
            for game in games:
                game.is_deleted = False
                game.deleted_at = None
                game.deleted_by = None
                count += 1

        if count > 0:
            self.db.commit()

        return count
