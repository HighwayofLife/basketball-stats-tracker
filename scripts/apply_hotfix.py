#!/usr/bin/env python3
"""Apply hotfix to production database to add missing columns."""

import os
import sys
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_hotfix():
    """Apply database schema hotfix."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    logger.info("Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            logger.info("Checking current schema...")
            # Check if columns exist
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('provider', 'provider_id', 'team_id')
            """))
            existing_columns = [row[0] for row in result]
            logger.info(f"Existing columns: {existing_columns}")
            
            # Add missing columns
            if 'provider' not in existing_columns:
                logger.info("Adding provider column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN provider VARCHAR(50) DEFAULT 'local'"))
                
            if 'provider_id' not in existing_columns:
                logger.info("Adding provider_id column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN provider_id VARCHAR(255)"))
                
            if 'team_id' not in existing_columns:
                logger.info("Adding team_id column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN team_id INTEGER"))
                conn.execute(text("ALTER TABLE users ADD CONSTRAINT fk_users_team_id FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE SET NULL"))
            
            # Mark migration as complete
            logger.info("Updating alembic version...")
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('4277cc4a9e9c') ON CONFLICT DO NOTHING"))
            
            # Commit transaction
            trans.commit()
            logger.info("✅ Hotfix applied successfully!")
            
    except Exception as e:
        logger.error(f"❌ Error applying hotfix: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_hotfix()