"""Base classes for implementing the Command pattern for undo/redo functionality."""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class Command(ABC):
    """Abstract base class for all commands that support undo/redo."""

    def __init__(self, db: Session, description: str | None = None):
        """Initialize the command.

        Args:
            db: Database session
            description: Optional description of the command
        """
        self.db = db
        self.command_id = str(uuid.uuid4())
        self.description = description
        self.executed = False
        self.undone = False
        self.audit_service = AuditLogService(db)
        self.executed_at: datetime | None = None
        self.undone_at: datetime | None = None

    @abstractmethod
    def execute(self) -> Any:
        """Execute the command.

        Returns:
            Result of the command execution
        """
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass

    def can_execute(self) -> bool:
        """Check if the command can be executed.

        Returns:
            True if command can be executed
        """
        return not self.executed

    def can_undo(self) -> bool:
        """Check if the command can be undone.

        Returns:
            True if command can be undone
        """
        return self.executed and not self.undone

    def _start_command(self) -> None:
        """Start the command context for audit logging."""
        self.audit_service.start_command(self.description)

    def _end_command(self) -> None:
        """End the command context."""
        self.audit_service.end_command()

    def _execute_wrapper(self) -> Any:
        """Wrapper for execute that handles common functionality.

        Returns:
            Result of the command execution
        """
        if not self.can_execute():
            raise ValueError("Command has already been executed")

        self._start_command()
        try:
            result = self.execute()
            self.executed = True
            self.executed_at = datetime.now(UTC)
            self.db.commit()
            return result
        except (ValueError, RuntimeError, AttributeError, TypeError, SQLAlchemyError):
            self.db.rollback()
            raise
        finally:
            self._end_command()

    def execute_command(self) -> Any:
        """Public method to execute the command with proper error handling.

        Returns:
            Result of the command execution
        """
        return self._execute_wrapper()

    def undo_command(self) -> None:
        """Public method to undo the command with proper error handling."""
        if not self.can_undo():
            raise ValueError("Command cannot be undone")

        self._start_command()
        try:
            self.undo()
            # Mark all audit logs for this command as undone
            # pylint: disable=import-outside-toplevel
            from app.data_access.crud.crud_audit_log import mark_command_as_undone

            mark_command_as_undone(self.db, self.command_id)

            self.undone = True
            self.undone_at = datetime.now(UTC)
            self.db.commit()
        except (ValueError, RuntimeError, AttributeError, TypeError, SQLAlchemyError):
            self.db.rollback()
            raise
        finally:
            self._end_command()


class MacroCommand(Command):
    """A command that executes multiple sub-commands."""

    def __init__(self, db: Session, commands: list[Command], description: str | None = None):
        """Initialize the macro command.

        Args:
            db: Database session
            commands: List of commands to execute
            description: Optional description of the macro command
        """
        super().__init__(db, description)
        self.commands = commands
        self.executed_commands: list[Command] = []

    def _rollback_executed(self) -> None:
        """Rollback any executed commands if an error occurs."""
        for command in reversed(self.executed_commands):
            if command.can_undo():
                try:
                    logger.debug("Rolling back command: %s", command.description)
                    command.undo_command()
                except (ValueError, RuntimeError, AttributeError, TypeError, SQLAlchemyError):
                    # Log but don't raise - we're already handling an error
                    logger.exception("Error during rollback of command: %s", command.description)


class CommandHistory:
    """Manages command execution history for undo/redo functionality."""

    def __init__(self, max_history: int = 100):
        """Initialize command history.

        Args:
            max_history: Maximum number of commands to keep in history
        """
        self.executed_commands: list[Command] = []
        self.undone_commands: list[Command] = []
        self.max_history = max_history

    def execute(self, command: Command) -> Any:
        """Add to history and execute the command.

        Args:
            command: Command to execute

        Returns:
            Result of command execution
        """
        result = command.execute_command()

        # Add to history
        self.executed_commands.append(command)

        # Clear redo stack when new command is executed
        self.undone_commands.clear()

        # Limit history size
        if len(self.executed_commands) > self.max_history:
            self.executed_commands.pop(0)

        return result

    def undo(self) -> bool:
        """Undo the last executed command."""
        if not self.can_undo():
            return False

        command = self.executed_commands.pop()
        command.undo_command()
        self.undone_commands.append(command)

        return True

    def redo(self) -> bool:
        """Redo the last undone command.

        Returns:
            True if redo was successful
        """
        if not self.can_redo():
            return False

        command = self.undone_commands.pop()
        command.execute_command()
        self.executed_commands.append(command)

        return True

    def can_undo(self) -> bool:
        """Check if there are commands to undo.

        Returns:
            True if undo is available
        """
        return len(self.executed_commands) > 0

    def can_redo(self) -> bool:
        """Check if there are commands to redo.

        Returns:
            True if redo is available
        """
        return len(self.undone_commands) > 0

    def clear(self) -> None:
        """Clear all command history."""
        self.executed_commands.clear()
        self.undone_commands.clear()

    def get_history(self) -> list[dict[str, Any]]:
        """Get a summary of command history.

        Returns:
            List of command summaries
        """
        history = []

        for command in self.executed_commands:
            history.append(
                {
                    "command_id": command.command_id,
                    "description": command.description,
                    "executed_at": command.executed_at,
                    "type": command.__class__.__name__,
                    "status": "executed",
                }
            )

        for command in reversed(self.undone_commands):
            history.append(
                {
                    "command_id": command.command_id,
                    "description": command.description,
                    "executed_at": command.executed_at,
                    "undone_at": command.undone_at,
                    "type": command.__class__.__name__,
                    "status": "undone",
                }
            )

        return history
