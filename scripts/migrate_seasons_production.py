#!/usr/bin/env python3
"""Production script to migrate games to seasons and update season statistics.

This script can be run in the production migration job to fix season assignments.
"""

import logging
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_access.db_session import get_db_session
from app.services.season_service import SeasonService
from app.services.season_stats_service import SeasonStatsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run season migration and stats update."""
    try:
        logger.info("Starting production season migration...")

        with get_db_session() as session:
            # Step 1: Migrate existing games to seasons
            logger.info("Step 1: Migrating games to seasons...")
            season_service = SeasonService(session)
            success, message = season_service.migrate_existing_games()

            if not success:
                logger.error(f"Season migration failed: {message}")
                sys.exit(1)

            logger.info(f"Season migration completed: {message}")

            # Step 2: Update season statistics
            logger.info("Step 2: Updating season statistics...")
            stats_service = SeasonStatsService(session)

            # Get all seasons to update stats for
            seasons = season_service.list_seasons()

            for season_data in seasons:
                season_code = season_data["code"]
                logger.info(f"Updating stats for season: {season_code}")
                stats_service.update_all_season_stats(season_code)

            logger.info("Season statistics update completed!")

        logger.info("✅ Production season migration completed successfully!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
