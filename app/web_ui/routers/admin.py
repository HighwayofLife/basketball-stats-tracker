"""Admin router for Basketball Stats Tracker."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User
from app.data_access import models
from app.data_access.crud.crud_audit_log import get_recent_audit_logs
from app.data_access.db_session import get_db_session
from app.services.data_correction_service import DataCorrectionService
from app.services.season_service import SeasonService
from app.web_ui.cache import get_cache_stats, invalidate_all_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["admin"])


@router.get("/player-game-stats/{stats_id}/quarters")
async def get_player_quarter_stats(stats_id: int):
    """Get quarter breakdown for a player's game stats."""
    try:
        with get_db_session() as session:
            game_stats = session.query(models.PlayerGameStats).filter_by(id=stats_id).first()

            if not game_stats:
                raise HTTPException(status_code=404, detail="Stats not found")

            quarters = []
            for quarter_stats in game_stats.quarter_stats:
                quarters.append(
                    {
                        "number": quarter_stats.quarter_number,
                        "ftm": quarter_stats.ftm,
                        "fta": quarter_stats.fta,
                        "fg2m": quarter_stats.fg2m,
                        "fg2a": quarter_stats.fg2a,
                        "fg3m": quarter_stats.fg3m,
                        "fg3a": quarter_stats.fg3a,
                    }
                )

            return {"statsId": stats_id, "quarters": quarters}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quarter stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get quarter stats") from e


@router.put("/player-game-stats/{stats_id}/quarters")
async def update_player_quarter_stats(stats_id: int, data: dict, current_user: User = Depends(get_current_user)):
    """Update quarter stats for a player with automatic total recalculation."""
    try:
        with get_db_session() as session:
            correction_service = DataCorrectionService(session)

            # Get the game stats
            game_stats = session.query(models.PlayerGameStats).filter_by(id=stats_id).first()
            if not game_stats:
                raise HTTPException(status_code=404, detail="Stats not found")

            # Update each quarter
            quarters_data = data.get("quarters", {})
            for quarter_num_str, quarter_updates in quarters_data.items():
                quarter_num = int(quarter_num_str)

                # Find the quarter stats
                quarter_stats = (
                    session.query(models.PlayerQuarterStats)
                    .filter_by(player_game_stat_id=stats_id, quarter_number=quarter_num)
                    .first()
                )

                if quarter_stats:
                    correction_service.update_player_quarter_stats(quarter_stats.id, quarter_updates)

            # Return updated totals
            session.refresh(game_stats)
            return {
                "total_ftm": game_stats.total_ftm,
                "total_fta": game_stats.total_fta,
                "total_2pm": game_stats.total_2pm,
                "total_2pa": game_stats.total_2pa,
                "total_3pm": game_stats.total_3pm,
                "total_3pa": game_stats.total_3pa,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating quarter stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to update quarter stats") from e


@router.post("/data-corrections/undo")
async def undo_last_correction(current_user: User = Depends(require_admin)):
    """Undo the last data correction."""
    try:
        with get_db_session() as session:
            correction_service = DataCorrectionService(session)
            success = correction_service.undo()

            return {"success": success, "can_undo": correction_service.can_undo()}

    except Exception as e:
        logger.error(f"Error undoing correction: {e}")
        raise HTTPException(status_code=500, detail="Failed to undo correction") from e


@router.post("/data-corrections/redo")
async def redo_last_correction():
    """Redo the last undone data correction."""
    try:
        with get_db_session() as session:
            correction_service = DataCorrectionService(session)
            success = correction_service.redo()

            return {"success": success, "can_redo": correction_service.can_redo()}

    except Exception as e:
        logger.error(f"Error redoing correction: {e}")
        raise HTTPException(status_code=500, detail="Failed to redo correction") from e


@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50, offset: int = 0, entity_type: str | None = None, user_id: int | None = None):
    """Get audit logs with pagination and filtering."""
    try:
        with get_db_session() as session:
            logs = get_recent_audit_logs(
                session,
                limit=limit + 1,  # Get one extra to check if there are more
                entity_type=entity_type,
                user_id=user_id,
            )

            has_more = len(logs) > limit
            logs = logs[:limit]  # Trim to requested limit

            return {
                "logs": [
                    {
                        "id": log.id,
                        "entity_type": log.entity_type,
                        "entity_id": log.entity_id,
                        "action": log.action,
                        "timestamp": log.timestamp.isoformat(),
                        "old_values": log.old_values,
                        "new_values": log.new_values,
                        "description": log.description,
                        "is_undone": log.is_undone,
                        "undo_timestamp": log.undo_timestamp.isoformat() if log.undo_timestamp else None,
                    }
                    for log in logs
                ],
                "hasMore": has_more,
            }
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit logs") from e


@router.post("/data-corrections/bulk-restore")
async def bulk_restore(data: dict):
    """Bulk restore deleted items of a specific type within a date range."""
    try:
        with get_db_session() as session:
            entity_type = data.get("entity_type")
            start_date_str = data.get("start_date")
            end_date_str = data.get("end_date")

            if not entity_type or not start_date_str or not end_date_str:
                raise HTTPException(status_code=400, detail="Missing required fields")

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            correction_service = DataCorrectionService(session)
            count = correction_service.restore_deleted_items(
                entity_type=entity_type, start_date=start_date, end_date=end_date
            )

            return {"success": True, "count": count}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error bulk restoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk restore") from e


@router.get("/data-corrections/history")
async def get_command_history():
    """Get command history for undo/redo operations."""
    try:
        with get_db_session() as session:
            correction_service = DataCorrectionService(session)
            history = correction_service.get_history()

            return {
                "history": history,
                "can_undo": correction_service.can_undo(),
                "can_redo": correction_service.can_redo(),
            }

    except Exception as e:
        logger.error(f"Error getting command history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get command history") from e


@router.get("/seasons")
async def get_seasons(current_user: User = Depends(require_admin)):
    """Get all seasons."""
    try:
        with get_db_session() as session:
            season_service = SeasonService(session)
            seasons = season_service.list_seasons()
            return {"seasons": seasons}
    except Exception as e:
        logger.error(f"Error getting seasons: {e}")
        raise HTTPException(status_code=500, detail="Failed to get seasons") from e


@router.get("/seasons/list")
async def list_seasons(current_user: User = Depends(require_admin)):
    """Get all seasons for use in dropdowns and selection."""
    try:
        with get_db_session() as session:
            season_service = SeasonService(session)
            seasons = season_service.list_seasons(include_inactive=True)
            # Extract year from start_date for dropdown display
            return [{"year": season["start_date"][:4]} for season in seasons]
    except Exception as e:
        logger.error(f"Error getting seasons list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get seasons") from e


@router.post("/seasons")
async def create_season(data: dict, current_user: User = Depends(require_admin)):
    """Create a new season."""
    try:
        with get_db_session() as session:
            season_service = SeasonService(session)

            from datetime import datetime

            start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()

            success, message, season = season_service.create_season(
                name=data["name"],
                code=data["code"],
                start_date=start_date,
                end_date=end_date,
                description=data.get("description"),
                set_as_active=data.get("set_as_active", False),
            )

            if success:
                return {
                    "success": True,
                    "message": message,
                    "season": {
                        "id": season.id,
                        "name": season.name,
                        "code": season.code,
                        "start_date": season.start_date.isoformat(),
                        "end_date": season.end_date.isoformat(),
                        "is_active": season.is_active,
                        "description": season.description,
                    },
                }
            else:
                raise HTTPException(status_code=400, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating season: {e}")
        raise HTTPException(status_code=500, detail="Failed to create season") from e


@router.put("/seasons/{season_id}")
async def update_season(season_id: int, data: dict, current_user: User = Depends(require_admin)):
    """Update a season."""
    try:
        with get_db_session() as session:
            season_service = SeasonService(session)

            start_date = None
            end_date = None
            if "start_date" in data:
                start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            if "end_date" in data:
                end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()

            success, message, season = season_service.update_season(
                season_id=season_id,
                name=data.get("name"),
                start_date=start_date,
                end_date=end_date,
                description=data.get("description"),
            )

            if success:
                return {"success": True, "message": message}
            else:
                raise HTTPException(status_code=400, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating season: {e}")
        raise HTTPException(status_code=500, detail="Failed to update season") from e


@router.post("/seasons/{season_id}/activate")
async def activate_season(season_id: int, current_user: User = Depends(require_admin)):
    """Set a season as active."""
    try:
        with get_db_session() as session:
            season_service = SeasonService(session)
            success, message = season_service.set_active_season(season_id)

            if success:
                return {"success": True, "message": message}
            else:
                raise HTTPException(status_code=400, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating season: {e}")
        raise HTTPException(status_code=500, detail="Failed to activate season") from e


@router.delete("/seasons/{season_id}")
async def delete_season(season_id: int, current_user: User = Depends(require_admin)):
    """Delete a season."""
    try:
        with get_db_session() as session:
            season_service = SeasonService(session)
            success, message = season_service.delete_season(season_id)

            if success:
                return {"success": True, "message": message}
            else:
                raise HTTPException(status_code=400, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting season: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete season") from e


# Cache Management Endpoints
@router.get("/cache/stats")
async def get_cache_statistics(current_user: User = Depends(require_admin)):
    """Get cache statistics for monitoring."""
    try:
        stats = await get_cache_stats()
        return {"success": True, "cache_stats": stats}
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats") from e


@router.post("/cache/invalidate")
async def invalidate_cache(current_user: User = Depends(require_admin)):
    """Manually invalidate all cache entries."""
    try:
        await invalidate_all_cache()
        logger.info(f"Cache manually invalidated by user {current_user.username}")
        return {"success": True, "message": "Cache invalidated successfully"}
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to invalidate cache") from e
