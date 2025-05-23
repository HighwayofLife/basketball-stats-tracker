"""Commands for team-related operations with undo/redo support."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.data_access.crud import get_team_by_id
from app.data_access.models import Team
from app.services.commands.base import Command


class UpdateTeamCommand(Command):
    """Command to update team details."""

    def __init__(self, db: Session, team_id: int, updates: dict[str, Any], description: str | None = None):
        """Initialize the update team command.

        Args:
            db: Database session
            team_id: ID of the team to update
            updates: Dictionary of fields to update
            description: Optional description
        """
        super().__init__(db, description or f"Update team {team_id}")
        self.team_id = team_id
        self.updates = updates
        self.old_values: dict[str, Any] = {}

    def execute(self) -> Team:
        """Execute the team update.

        Returns:
            Updated team object
        """
        team = get_team_by_id(self.db, self.team_id)
        if not team:
            raise ValueError(f"Team with ID {self.team_id} not found")

        # Store old values for undo
        for field, new_value in self.updates.items():
            if hasattr(team, field):
                self.old_values[field] = getattr(team, field)
                setattr(team, field, new_value)

        # Log the update
        self.audit_service.log_update(
            entity_type="team",
            entity_id=self.team_id,
            old_values=self.old_values,
            new_values=self.updates,
            description=self.description,
        )

        self.db.flush()
        return team

    def undo(self) -> None:
        """Undo the team update."""
        team = get_team_by_id(self.db, self.team_id)
        if not team:
            raise ValueError(f"Team with ID {self.team_id} not found")

        # Restore old values
        for field, old_value in self.old_values.items():
            setattr(team, field, old_value)

        # Log the undo
        self.audit_service.log_update(
            entity_type="team",
            entity_id=self.team_id,
            old_values=self.updates,
            new_values=self.old_values,
            description=f"Undo: {self.description}",
        )

        self.db.flush()


class DeleteTeamCommand(Command):
    """Command to soft delete a team."""

    def __init__(self, db: Session, team_id: int, user_id: int | None = None, description: str | None = None):
        """Initialize the delete team command.

        Args:
            db: Database session
            team_id: ID of the team to delete
            user_id: ID of user performing the delete
            description: Optional description
        """
        super().__init__(db, description or f"Delete team {team_id}")
        self.team_id = team_id
        self.user_id = user_id

    def execute(self) -> None:
        """Execute the team deletion (soft delete)."""
        team = get_team_by_id(self.db, self.team_id)
        if not team:
            raise ValueError(f"Team with ID {self.team_id} not found")

        if team.is_deleted:
            raise ValueError(f"Team {self.team_id} is already deleted")

        # Check if team has active players
        active_players = [p for p in team.players if p.is_active and not p.is_deleted]
        if active_players:
            raise ValueError(f"Cannot delete team {self.team_id} with {len(active_players)} active players")

        # Soft delete the team
        team.is_deleted = True
        team.deleted_at = datetime.utcnow()
        team.deleted_by = self.user_id

        # Log the deletion
        self.audit_service.log_delete(
            entity_type="team",
            entity_id=self.team_id,
            old_values={"is_deleted": False},
            user_id=self.user_id,
            description=self.description,
        )

        self.db.flush()

    def undo(self) -> None:
        """Undo the team deletion (restore)."""
        team = get_team_by_id(self.db, self.team_id)
        if not team:
            raise ValueError(f"Team with ID {self.team_id} not found")

        if not team.is_deleted:
            raise ValueError(f"Team {self.team_id} is not deleted")

        # Restore the team
        team.is_deleted = False
        team.deleted_at = None
        team.deleted_by = None

        # Log the restore
        self.audit_service.log_restore(
            entity_type="team",
            entity_id=self.team_id,
            restored_values={"is_deleted": False},
            user_id=self.user_id,
            description=f"Restore: {self.description}",
        )

        self.db.flush()


class RenameTeamCommand(Command):
    """Command to rename a team."""

    def __init__(self, db: Session, team_id: int, new_name: str, description: str | None = None):
        """Initialize the rename team command.

        Args:
            db: Database session
            team_id: ID of the team to rename
            new_name: New team name
            description: Optional description
        """
        super().__init__(db, description or f"Rename team {team_id} to {new_name}")
        self.team_id = team_id
        self.new_name = new_name
        self.old_name: str | None = None

    def execute(self) -> Team:
        """Execute the team rename.

        Returns:
            Updated team object
        """
        team = get_team_by_id(self.db, self.team_id)
        if not team:
            raise ValueError(f"Team with ID {self.team_id} not found")

        # Check if new name is already taken
        # pylint: disable=import-outside-toplevel
        from app.data_access.crud import get_team_by_name

        existing_team = get_team_by_name(self.db, self.new_name)
        if existing_team and existing_team.id != self.team_id:
            raise ValueError(f"Team name '{self.new_name}' is already taken")

        # Store old name for undo
        self.old_name = team.name

        # Update name
        team.name = self.new_name

        # Log the rename
        self.audit_service.log_update(
            entity_type="team",
            entity_id=self.team_id,
            old_values={"name": self.old_name},
            new_values={"name": self.new_name},
            description=self.description,
        )

        self.db.flush()
        return team

    def undo(self) -> None:
        """Undo the team rename."""
        team = get_team_by_id(self.db, self.team_id)
        if not team:
            raise ValueError(f"Team with ID {self.team_id} not found")

        if self.old_name is None:
            raise ValueError("Cannot undo rename: original name is None")

        # Restore old name
        team.name = self.old_name

        # Log the undo
        self.audit_service.log_update(
            entity_type="team",
            entity_id=self.team_id,
            old_values={"name": self.new_name},
            new_values={"name": self.old_name},
            description=f"Undo: {self.description}",
        )

        self.db.flush()
