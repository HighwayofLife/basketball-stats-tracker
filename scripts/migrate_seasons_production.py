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

            # Step 3: Update game scores for games that don't have scores populated
            logger.info("Step 3: Updating missing game scores...")
            games_updated = 0

            # Find games with NULL or 0 scores but have player statistics
            from app.data_access.models import Game, PlayerGameStats
            from sqlalchemy import or_, and_

            games_without_scores = (
                session.query(Game)
                .filter(
                    or_(
                        Game.playing_team_score.is_(None),
                        Game.opponent_team_score.is_(None),
                        and_(Game.playing_team_score == 0, Game.opponent_team_score == 0),
                    )
                )
                .all()
            )

            for game in games_without_scores:
                # Check if this game has player statistics
                player_stats = session.query(PlayerGameStats).filter(PlayerGameStats.game_id == game.id).all()

                if player_stats:
                    # Calculate scores from player statistics
                    home_score = 0
                    away_score = 0

                    for stat in player_stats:
                        player_points = stat.total_ftm + (stat.total_2pm * 2) + (stat.total_3pm * 3)

                        if stat.player.team_id == game.playing_team_id:
                            home_score += player_points
                        elif stat.player.team_id == game.opponent_team_id:
                            away_score += player_points

                    # Update game scores
                    game.playing_team_score = home_score
                    game.opponent_team_score = away_score
                    games_updated += 1

            session.commit()
            logger.info(f"Updated scores for {games_updated} games")

        logger.info("✅ Production season migration completed successfully!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
