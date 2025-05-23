"""Command pattern implementation for undo/redo functionality."""

from app.services.commands.base import Command, CommandHistory, MacroCommand
from app.services.commands.game_commands import (
    BatchUpdateGameStatsCommand,
    DeleteGameCommand,
    UpdateGameCommand,
    UpdatePlayerGameStatsCommand,
    UpdatePlayerQuarterStatsCommand,
)
from app.services.commands.player_commands import (
    ChangeJerseyNumberCommand,
    DeletePlayerCommand,
    TransferPlayerCommand,
    UpdatePlayerCommand,
)
from app.services.commands.team_commands import DeleteTeamCommand, RenameTeamCommand, UpdateTeamCommand

__all__ = [
    # Base classes
    "Command",
    "MacroCommand",
    "CommandHistory",
    # Game commands
    "UpdateGameCommand",
    "DeleteGameCommand",
    "UpdatePlayerGameStatsCommand",
    "UpdatePlayerQuarterStatsCommand",
    "BatchUpdateGameStatsCommand",
    # Player commands
    "UpdatePlayerCommand",
    "DeletePlayerCommand",
    "TransferPlayerCommand",
    "ChangeJerseyNumberCommand",
    # Team commands
    "UpdateTeamCommand",
    "DeleteTeamCommand",
    "RenameTeamCommand",
]
