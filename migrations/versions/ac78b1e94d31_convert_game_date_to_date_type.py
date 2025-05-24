"""
Convert Game.date field from String to Date type.

Revision ID: ac78b1e94d31
Revises: 834c9663d23c
Create Date: 2025-05-21 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'ac78b1e94d31'
down_revision = '834c9663d23c'
branch_labels = None
depends_on = None


def upgrade():
    # Create a temporary table with the date column as Date type
    op.execute('''
    CREATE TABLE games_temp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        playing_team_id INTEGER NOT NULL,
        opponent_team_id INTEGER NOT NULL,
        FOREIGN KEY (playing_team_id) REFERENCES teams (id),
        FOREIGN KEY (opponent_team_id) REFERENCES teams (id)
    )
    ''')

    # Copy data from the old table to the new one, converting string dates to date objects
    op.execute('''
    INSERT INTO games_temp (id, date, playing_team_id, opponent_team_id)
    SELECT id, date(date), playing_team_id, opponent_team_id
    FROM games
    ''')

    # Drop the old table
    op.drop_table('games')

    # Rename the new table to the original name
    op.rename_table('games_temp', 'games')


def downgrade():
    # Create a temporary table with the date column as String type
    op.execute('''
    CREATE TABLE games_temp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date VARCHAR NOT NULL,
        playing_team_id INTEGER NOT NULL,
        opponent_team_id INTEGER NOT NULL,
        FOREIGN KEY (playing_team_id) REFERENCES teams (id),
        FOREIGN KEY (opponent_team_id) REFERENCES teams (id)
    )
    ''')

    # Copy data from the current table to the temporary one, converting date objects to strings
    op.execute('''
    INSERT INTO games_temp (id, date, playing_team_id, opponent_team_id)
    SELECT id, strftime('%Y-%m-%d', date), playing_team_id, opponent_team_id
    FROM games
    ''')

    # Drop the current table
    op.drop_table('games')

    # Rename the temporary table to the original name
    op.rename_table('games_temp', 'games')
