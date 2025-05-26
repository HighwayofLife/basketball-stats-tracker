"""fix_jersey_number_and_player_constraints

Revision ID: 4d2154170d95
Revises: 48b56284cfab
Create Date: 2025-05-26 01:33:44.975757

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d2154170d95'
down_revision = '48b56284cfab'
branch_labels = None
depends_on = None


def upgrade():
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('players', schema=None) as batch_op:
        # Add new string column for jersey number to handle "0" vs "00"
        batch_op.add_column(sa.Column('jersey_number_str', sa.String(10), nullable=True))
        
    # Copy data from integer to string
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE players 
        SET jersey_number_str = CAST(jersey_number AS TEXT)
    """))
    
    # Continue with batch mode to complete the transformation
    with op.batch_alter_table('players', schema=None) as batch_op:
        # Make the new column non-nullable
        batch_op.alter_column('jersey_number_str', nullable=False)
        
        # Drop old constraints first
        batch_op.drop_constraint('uq_player_team_jersey', type_='unique')
        batch_op.drop_constraint('uq_player_team_name', type_='unique')
        
        # Drop the old integer column
        batch_op.drop_column('jersey_number')
        
        # Rename the new column
        batch_op.alter_column('jersey_number_str', new_column_name='jersey_number')
        
        # Recreate the unique constraints with the new string column
        batch_op.create_unique_constraint('uq_player_team_jersey', ['team_id', 'jersey_number'])
        batch_op.create_unique_constraint('uq_player_team_name', ['team_id', 'name'])


def downgrade():
    # Reverse the process using batch mode
    with op.batch_alter_table('players', schema=None) as batch_op:
        # Drop current constraints
        batch_op.drop_constraint('uq_player_team_jersey', type_='unique')
        batch_op.drop_constraint('uq_player_team_name', type_='unique')
        
        # Add integer column
        batch_op.add_column(sa.Column('jersey_number_int', sa.Integer(), nullable=True))
    
    # Convert string back to integer (will lose leading zeros)
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE players 
        SET jersey_number_int = CAST(jersey_number AS INTEGER)
    """))
    
    with op.batch_alter_table('players', schema=None) as batch_op:
        # Make the new column non-nullable
        batch_op.alter_column('jersey_number_int', nullable=False)
        
        # Drop the string column
        batch_op.drop_column('jersey_number')
        
        # Rename back
        batch_op.alter_column('jersey_number_int', new_column_name='jersey_number')
        
        # Recreate both constraints  
        batch_op.create_unique_constraint('uq_player_team_jersey', ['team_id', 'jersey_number'])
        batch_op.create_unique_constraint('uq_player_team_name', ['team_id', 'name'])
