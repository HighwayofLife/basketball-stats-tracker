"""Service for managing audit logs and tracking data changes."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.data_access.models import AuditLog


class AuditLogService:
    """Service for creating and managing audit logs."""

    def __init__(self, db: Session):
        """Initialize the audit log service.

        Args:
            db: The database session
        """
        self.db = db
        self._command_id: str | None = None

    def start_command(self, description: str | None = None) -> str:
        """Start a new command context for grouping related changes.

        Args:
            description: Optional description of the command

        Returns:
            The command ID for this group of changes
        """
        self._command_id = str(uuid.uuid4())
        return self._command_id

    def end_command(self) -> None:
        """End the current command context."""
        self._command_id = None

    def log_create(
        self,
        entity_type: str,
        entity_id: int,
        new_values: dict[str, Any],
        user_id: int | None = None,
        description: str | None = None,
    ) -> AuditLog:
        """Log a create operation.

        Args:
            entity_type: Type of entity (e.g., 'game', 'player', 'team')
            entity_id: ID of the created entity
            new_values: The values of the created entity
            user_id: Optional user ID who performed the action
            description: Optional description of the change

        Returns:
            The created audit log entry
        """
        audit_log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action="create",
            user_id=user_id,
            new_values=self._serialize_values(new_values),
            command_id=self._command_id,
            description=description,
        )
        self.db.add(audit_log)
        self.db.flush()
        return audit_log

    def log_update(
        self,
        entity_type: str,
        entity_id: int,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
        user_id: int | None = None,
        description: str | None = None,
    ) -> AuditLog | None:
        """Log an update operation.

        Args:
            entity_type: Type of entity (e.g., 'game', 'player', 'team')
            entity_id: ID of the updated entity
            old_values: The values before the update
            new_values: The values after the update
            user_id: Optional user ID who performed the action
            description: Optional description of the change

        Returns:
            The created audit log entry
        """
        # Only log changed values
        changed_old = {}
        changed_new = {}
        for key, new_value in new_values.items():
            if key in old_values and old_values[key] != new_value:
                changed_old[key] = old_values[key]
                changed_new[key] = new_value

        if not changed_new:
            return None  # No changes to log

        audit_log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action="update",
            user_id=user_id,
            old_values=self._serialize_values(changed_old),
            new_values=self._serialize_values(changed_new),
            command_id=self._command_id,
            description=description,
        )
        self.db.add(audit_log)
        self.db.flush()
        return audit_log

    def log_delete(
        self,
        entity_type: str,
        entity_id: int,
        old_values: dict[str, Any],
        user_id: int | None = None,
        description: str | None = None,
    ) -> AuditLog:
        """Log a delete operation.

        Args:
            entity_type: Type of entity (e.g., 'game', 'player', 'team')
            entity_id: ID of the deleted entity
            old_values: The values of the deleted entity
            user_id: Optional user ID who performed the action
            description: Optional description of the change

        Returns:
            The created audit log entry
        """
        audit_log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action="delete",
            user_id=user_id,
            old_values=self._serialize_values(old_values),
            command_id=self._command_id,
            description=description,
        )
        self.db.add(audit_log)
        self.db.flush()
        return audit_log

    def log_restore(
        self,
        entity_type: str,
        entity_id: int,
        restored_values: dict[str, Any],
        user_id: int | None = None,
        description: str | None = None,
    ) -> AuditLog:
        """Log a restore operation.

        Args:
            entity_type: Type of entity (e.g., 'game', 'player', 'team')
            entity_id: ID of the restored entity
            restored_values: The values of the restored entity
            user_id: Optional user ID who performed the action
            description: Optional description of the change

        Returns:
            The created audit log entry
        """
        audit_log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action="restore",
            user_id=user_id,
            new_values=self._serialize_values(restored_values),
            command_id=self._command_id,
            description=description,
        )
        self.db.add(audit_log)
        self.db.flush()
        return audit_log

    def mark_as_undone(self, audit_log_id: int) -> None:
        """Mark an audit log entry as undone.

        Args:
            audit_log_id: ID of the audit log entry to mark as undone
        """
        audit_log = self.db.query(AuditLog).filter_by(id=audit_log_id).first()
        if audit_log:
            audit_log.is_undone = True
            audit_log.undo_timestamp = datetime.utcnow()
            self.db.flush()

    def get_command_logs(self, command_id: str) -> list[AuditLog]:
        """Get all audit logs for a specific command.

        Args:
            command_id: The command ID to retrieve logs for

        Returns:
            List of audit logs for the command
        """
        return self.db.query(AuditLog).filter_by(command_id=command_id).order_by(AuditLog.timestamp).all()

    def get_entity_history(self, entity_type: str, entity_id: int, include_undone: bool = False) -> list[AuditLog]:
        """Get the change history for a specific entity.

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            include_undone: Whether to include undone changes

        Returns:
            List of audit logs for the entity
        """
        query = self.db.query(AuditLog).filter_by(entity_type=entity_type, entity_id=entity_id)

        if not include_undone:
            query = query.filter_by(is_undone=False)

        return query.order_by(AuditLog.timestamp.desc()).all()

    def get_recent_changes(
        self, limit: int = 50, entity_type: str | None = None, user_id: int | None = None
    ) -> list[AuditLog]:
        """Get recent changes with optional filters.

        Args:
            limit: Maximum number of changes to return
            entity_type: Optional filter by entity type
            user_id: Optional filter by user

        Returns:
            List of recent audit logs
        """
        query = self.db.query(AuditLog).filter_by(is_undone=False)

        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def _serialize_values(self, values: dict[str, Any]) -> dict[str, Any]:
        """Serialize values for storage in JSON column.

        Args:
            values: Dictionary of values to serialize

        Returns:
            Serialized values safe for JSON storage
        """
        serialized = {}
        for key, value in values.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif hasattr(value, "__dict__"):
                # Skip complex objects, store only their ID if available
                if hasattr(value, "id"):
                    serialized[f"{key}_id"] = value.id
            else:
                serialized[key] = value
        return serialized
