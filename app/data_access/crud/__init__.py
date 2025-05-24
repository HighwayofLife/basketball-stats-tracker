"""
CRUD operations package for database access.
"""

# Import all CRUD functions
from app.data_access.crud.crud_audit_log import (
    create_audit_log,
    get_audit_log,
    get_audit_logs_by_command,
    get_audit_logs_by_entity,
    get_recent_audit_logs,
    mark_audit_log_as_undone,
    mark_command_as_undone,
)
from app.data_access.crud.crud_game import (
    create_game,
    get_all_games,
    get_game_by_id,
    get_games_by_date_range,
    get_games_by_team,
)
from app.data_access.crud.crud_player import (
    create_player,
    get_all_players,
    get_player_by_id,
    get_player_by_team_and_jersey,
    get_players_by_team,
)
from app.data_access.crud.crud_player_game_stats import (
    create_player_game_stats,
    get_player_game_stats,
    get_player_game_stats_by_game,
    update_player_game_stats_totals,
)
from app.data_access.crud.crud_player_quarter_stats import (
    create_player_quarter_stats,
    get_player_quarter_stats,
    get_quarter_stats_by_quarter,
)
from app.data_access.crud.crud_player_season_stats import (
    create_player_season_stats,
    get_player_all_seasons,
    get_player_season_stats,
    get_season_players,
    update_player_season_stats,
)
from app.data_access.crud.crud_team import create_team, get_all_teams, get_team_by_id, get_team_by_name
from app.data_access.crud.crud_team_season_stats import (
    create_team_season_stats,
    get_season_teams,
    get_team_all_seasons,
    get_team_season_stats,
    update_team_season_stats,
)

# Define public API
__all__ = [
    # Audit Log CRUD
    "create_audit_log",
    "get_audit_log",
    "get_audit_logs_by_command",
    "get_audit_logs_by_entity",
    "get_recent_audit_logs",
    "mark_audit_log_as_undone",
    "mark_command_as_undone",
    # Team CRUD
    "create_team",
    "get_team_by_name",
    "get_team_by_id",
    "get_all_teams",
    # Player CRUD
    "create_player",
    "get_player_by_team_and_jersey",
    "get_player_by_id",
    "get_players_by_team",
    "get_all_players",
    # Game CRUD
    "create_game",
    "get_game_by_id",
    "get_games_by_team",
    "get_games_by_date_range",
    "get_all_games",
    # PlayerGameStats CRUD
    "create_player_game_stats",
    "update_player_game_stats_totals",
    "get_player_game_stats_by_game",
    "get_player_game_stats",
    # PlayerQuarterStats CRUD
    "create_player_quarter_stats",
    "get_player_quarter_stats",
    "get_quarter_stats_by_quarter",
    # PlayerSeasonStats CRUD
    "create_player_season_stats",
    "get_player_season_stats",
    "get_player_all_seasons",
    "get_season_players",
    "update_player_season_stats",
    # TeamSeasonStats CRUD
    "create_team_season_stats",
    "get_team_season_stats",
    "get_team_all_seasons",
    "get_season_teams",
    "update_team_season_stats",
]
