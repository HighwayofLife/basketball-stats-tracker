"""Commands for player-related operations with undo/redo support."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.data_access.crud import get_player_by_id
from app.data_access.models import Player
from app.services.commands.base import Command


class UpdatePlayerCommand(Command):
    """Command to update player details."""

    def __init__(self, db: Session, player_id: int, updates: dict[str, Any], description: str | None = None):
        """Initialize the update player command.

        Args:
            db: Database session
            player_id: ID of the player to update
            updates: Dictionary of fields to update
            description: Optional description
        """
        super().__init__(db, description or f"Update player {player_id}")
        self.player_id = player_id
        self.updates = updates
        self.old_values: dict[str, Any] = {}

    def execute(self) -> Player:
        """Execute the player update.

        Returns:
            Updated player object
        """
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        # Store old values for undo
        for field, new_value in self.updates.items():
            if hasattr(player, field):
                self.old_values[field] = getattr(player, field)
                setattr(player, field, new_value)

        # Log the update
        self.audit_service.log_update(
            entity_type="player",
            entity_id=self.player_id,
            old_values=self.old_values,
            new_values=self.updates,
            description=self.description,
        )

        self.db.flush()
        return player

    def undo(self) -> None:
        """Undo the player update."""
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        # Restore old values
        for field, old_value in self.old_values.items():
            setattr(player, field, old_value)

        # Log the undo
        self.audit_service.log_update(
            entity_type="player",
            entity_id=self.player_id,
            old_values=self.updates,
            new_values=self.old_values,
            description=f"Undo: {self.description}",
        )

        self.db.flush()


class DeletePlayerCommand(Command):
    """Command to soft delete a player."""

    def __init__(self, db: Session, player_id: int, user_id: int | None = None, description: str | None = None):
        """Initialize the delete player command.

        Args:
            db: Database session
            player_id: ID of the player to delete
            user_id: ID of user performing the delete
            description: Optional description
        """
        super().__init__(db, description or f"Delete player {player_id}")
        self.player_id = player_id
        self.user_id = user_id

    def execute(self) -> None:
        """Execute the player deletion (soft delete)."""
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        if player.is_deleted:
            raise ValueError(f"Player {self.player_id} is already deleted")

        # Soft delete the player
        player.is_deleted = True
        player.deleted_at = datetime.utcnow()
        player.deleted_by = self.user_id

        # Also deactivate the player
        player.is_active = False

        # Log the deletion
        self.audit_service.log_delete(
            entity_type="player",
            entity_id=self.player_id,
            old_values={"is_deleted": False, "is_active": player.is_active},
            user_id=self.user_id,
            description=self.description,
        )

        self.db.flush()

    def undo(self) -> None:
        """Undo the player deletion (restore)."""
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        if not player.is_deleted:
            raise ValueError(f"Player {self.player_id} is not deleted")

        # Restore the player
        player.is_deleted = False
        player.deleted_at = None
        player.deleted_by = None

        # Reactivate the player
        player.is_active = True

        # Log the restore
        self.audit_service.log_restore(
            entity_type="player",
            entity_id=self.player_id,
            restored_values={"is_deleted": False, "is_active": True},
            user_id=self.user_id,
            description=f"Restore: {self.description}",
        )

        self.db.flush()


class TransferPlayerCommand(Command):
    """Command to transfer a player to a different team."""

    def __init__(self, db: Session, player_id: int, new_team_id: int, description: str | None = None):
        """Initialize the transfer player command.

        Args:
            db: Database session
            player_id: ID of the player to transfer
            new_team_id: ID of the new team
            description: Optional description
        """
        super().__init__(db, description or f"Transfer player {player_id} to team {new_team_id}")
        self.player_id = player_id
        self.new_team_id = new_team_id
        self.old_team_id: int | None = None

    def execute(self) -> Player:
        """Execute the player transfer.

        Returns:
            Updated player object
        """
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        # Store old team for undo
        self.old_team_id = player.team_id

        # Check if jersey number is already taken on new team
        # pylint: disable=import-outside-toplevel
        from app.data_access.crud import get_player_by_team_and_jersey

        existing_player = get_player_by_team_and_jersey(self.db, self.new_team_id, player.jersey_number)
        if existing_player and existing_player.id != self.player_id:
            raise ValueError(f"Jersey number {player.jersey_number} is already taken on team {self.new_team_id}")

        # Update team
        player.team_id = self.new_team_id

        # Log the transfer
        self.audit_service.log_update(
            entity_type="player",
            entity_id=self.player_id,
            old_values={"team_id": self.old_team_id},
            new_values={"team_id": self.new_team_id},
            description=self.description,
        )

        self.db.flush()
        return player

    def undo(self) -> None:
        """Undo the player transfer."""
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        if self.old_team_id is None:
            raise ValueError("Cannot undo transfer: original team ID is None")

        # Restore old team
        player.team_id = self.old_team_id

        # Log the undo
        self.audit_service.log_update(
            entity_type="player",
            entity_id=self.player_id,
            old_values={"team_id": self.new_team_id},
            new_values={"team_id": self.old_team_id},
            description=f"Undo: {self.description}",
        )

        self.db.flush()


class ChangeJerseyNumberCommand(Command):
    """Command to change a player's jersey number."""

    def __init__(self, db: Session, player_id: int, new_jersey_number: int, description: str | None = None):
        """Initialize the change jersey number command.

        Args:
            db: Database session
            player_id: ID of the player
            new_jersey_number: New jersey number
            description: Optional description
        """
        super().__init__(db, description or f"Change jersey number for player {player_id} to {new_jersey_number}")
        self.player_id = player_id
        self.new_jersey_number = new_jersey_number
        self.old_jersey_number: int | None = None

    def execute(self) -> Player:
        """Execute the jersey number change.

        Returns:
            Updated player object
        """
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        # Store old jersey number for undo
        self.old_jersey_number = player.jersey_number

        # Check if new jersey number is already taken
        from app.data_access.crud import get_player_by_team_and_jersey

        existing_player = get_player_by_team_and_jersey(self.db, player.team_id, self.new_jersey_number)
        if existing_player and existing_player.id != self.player_id:
            raise ValueError(f"Jersey number {self.new_jersey_number} is already taken on this team")

        # Update jersey number
        player.jersey_number = self.new_jersey_number

        # Log the change
        self.audit_service.log_update(
            entity_type="player",
            entity_id=self.player_id,
            old_values={"jersey_number": self.old_jersey_number},
            new_values={"jersey_number": self.new_jersey_number},
            description=self.description,
        )

        self.db.flush()
        return player

    def undo(self) -> None:
        """Undo the jersey number change."""
        player = get_player_by_id(self.db, self.player_id)
        if not player:
            raise ValueError(f"Player with ID {self.player_id} not found")

        # Restore old jersey number
        if self.old_jersey_number is not None:
            player.jersey_number = self.old_jersey_number

        # Log the undo
        self.audit_service.log_update(
            entity_type="player",
            entity_id=self.player_id,
            old_values={"jersey_number": self.new_jersey_number},
            new_values={"jersey_number": self.old_jersey_number},
            description=f"Undo: {self.description}",
        )

        self.db.flush()
