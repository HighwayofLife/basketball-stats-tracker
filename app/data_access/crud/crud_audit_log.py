"""CRUD operations for audit logs."""

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.data_access.models import AuditLog


def create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    old_values: dict | None = None,
    new_values: dict | None = None,
    user_id: int | None = None,
    command_id: str | None = None,
    description: str | None = None,
) -> AuditLog:
    """Create a new audit log entry.

    Args:
        db: Database session
        entity_type: Type of entity being audited
        entity_id: ID of the entity
        action: Action performed (create, update, delete, restore)
        old_values: Values before the change
        new_values: Values after the change
        user_id: ID of user who performed the action
        command_id: UUID for grouping related changes
        description: Optional description of the change

    Returns:
        Created audit log entry
    """
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
        user_id=user_id,
        command_id=command_id,
        description=description,
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def get_audit_log(db: Session, audit_log_id: int) -> AuditLog | None:
    """Get an audit log entry by ID.

    Args:
        db: Database session
        audit_log_id: ID of the audit log entry

    Returns:
        Audit log entry if found, None otherwise
    """
    return db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()


def get_audit_logs_by_command(db: Session, command_id: str) -> list[AuditLog]:
    """Get all audit logs for a specific command.

    Args:
        db: Database session
        command_id: Command ID to filter by

    Returns:
        List of audit logs for the command
    """
    return db.query(AuditLog).filter(AuditLog.command_id == command_id).order_by(AuditLog.timestamp).all()


def get_audit_logs_by_entity(
    db: Session, entity_type: str, entity_id: int, include_undone: bool = False
) -> list[AuditLog]:
    """Get all audit logs for a specific entity.

    Args:
        db: Database session
        entity_type: Type of entity
        entity_id: ID of the entity
        include_undone: Whether to include undone changes

    Returns:
        List of audit logs for the entity
    """
    query = db.query(AuditLog).filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)

    if not include_undone:
        query = query.filter(AuditLog.is_undone.is_(False))

    return query.order_by(desc(AuditLog.timestamp)).all()


def get_recent_audit_logs(
    db: Session,
    limit: int = 50,
    entity_type: str | None = None,
    user_id: int | None = None,
    include_undone: bool = False,
) -> list[AuditLog]:
    """Get recent audit logs with optional filters.

    Args:
        db: Database session
        limit: Maximum number of logs to return
        entity_type: Optional filter by entity type
        user_id: Optional filter by user ID
        include_undone: Whether to include undone changes

    Returns:
        List of recent audit logs
    """
    query = db.query(AuditLog)

    if not include_undone:
        query = query.filter(AuditLog.is_undone.is_(False))

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()


def mark_audit_log_as_undone(db: Session, audit_log_id: int) -> AuditLog | None:
    """Mark an audit log entry as undone.

    Args:
        db: Database session
        audit_log_id: ID of the audit log to mark as undone

    Returns:
        Updated audit log entry if found, None otherwise
    """
    audit_log = get_audit_log(db, audit_log_id)
    if audit_log:
        audit_log.is_undone = True
        audit_log.undo_timestamp = datetime.utcnow()
        db.flush()
    return audit_log


def mark_command_as_undone(db: Session, command_id: str) -> int:
    """Mark all audit logs for a command as undone.

    Args:
        db: Database session
        command_id: Command ID to mark as undone

    Returns:
        Number of audit logs marked as undone
    """
    audit_logs = get_audit_logs_by_command(db, command_id)
    count = 0
    for audit_log in audit_logs:
        if not audit_log.is_undone:
            audit_log.is_undone = True
            audit_log.undo_timestamp = datetime.utcnow()
            count += 1

    if count > 0:
        db.flush()

    return count
