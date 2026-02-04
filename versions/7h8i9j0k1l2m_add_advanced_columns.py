"""add_advanced_columns

Revision ID: 7h8i9j0k1l2m
Revises: 6g7h8i9j0k1l
Create Date: 2026-02-03 19:49:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7h8i9j0k1l2m'
down_revision = '6g7h8i9j0k1l'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Advanced: Quality (Phase IX)
    op.add_column('agent_configs', sa.Column('noise_suppression_level', sa.String(), server_default='High', nullable=True))
    op.add_column('agent_configs', sa.Column('audio_codec', sa.String(), server_default='PCMU', nullable=True))
    op.add_column('agent_configs', sa.Column('enable_backchannel', sa.Boolean(), server_default='false', nullable=True))
    
    # Advanced: Safety Limits
    op.add_column('agent_configs', sa.Column('max_duration_seconds', sa.Integer(), server_default='600', nullable=True))
    op.add_column('agent_configs', sa.Column('max_retries', sa.Integer(), server_default='2', nullable=True))
    op.add_column('agent_configs', sa.Column('inactivity_message', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_configs', 'inactivity_message')
    op.drop_column('agent_configs', 'max_retries')
    op.drop_column('agent_configs', 'max_duration_seconds')
    op.drop_column('agent_configs', 'enable_backchannel')
    op.drop_column('agent_configs', 'audio_codec')
    op.drop_column('agent_configs', 'noise_suppression_level')
