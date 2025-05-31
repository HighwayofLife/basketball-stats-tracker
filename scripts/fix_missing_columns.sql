-- Add missing OAuth columns to users table
-- This is a hotfix for production database schema issues

-- Add provider column
ALTER TABLE users ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'local';

-- Add provider_id column  
ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_id VARCHAR(255);

-- Add team_id column
ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id INTEGER;

-- Add foreign key constraint for team_id
ALTER TABLE users ADD CONSTRAINT fk_users_team_id FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE SET NULL;

-- Update alembic version to mark these migrations as complete
INSERT INTO alembic_version (version_num) VALUES ('4277cc4a9e9c') ON CONFLICT DO NOTHING;