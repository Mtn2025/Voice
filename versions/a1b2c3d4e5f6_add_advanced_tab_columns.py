"""add_advanced_tab_columns

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-01-31 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADVANCED TAB (PHASE IX)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    # 1. Quality & Codecs
    if 'noise_suppression_level' not in columns:
        op.add_column('agent_configs', sa.Column('noise_suppression_level', sa.String(), server_default='balanced', nullable=True))
    if 'audio_codec' not in columns:
        op.add_column('agent_configs', sa.Column('audio_codec', sa.String(), server_default='PCMU', nullable=True))
    if 'enable_backchannel' not in columns:
        op.add_column('agent_configs', sa.Column('enable_backchannel', sa.Boolean(), server_default='false', nullable=True))
    
    # 2. Safety Limits (Legacy but requested)
    if 'max_duration' not in columns:
        op.add_column('agent_configs', sa.Column('max_duration', sa.Integer(), server_default='600', nullable=True))
    if 'inactivity_max_retries' not in columns:
        op.add_column('agent_configs', sa.Column('inactivity_max_retries', sa.Integer(), server_default='2', nullable=True))
    if 'idle_message' not in columns:
        op.add_column('agent_configs', sa.Column('idle_message', sa.Text(), server_default='¿Sigues ahí?', nullable=True))


def downgrade() -> None:
    op.drop_column('agent_config', 'idle_message')
    op.drop_column('agent_config', 'inactivity_max_retries')
    op.drop_column('agent_config', 'max_duration')
    op.drop_column('agent_config', 'enable_backchannel')
    op.drop_column('agent_config', 'audio_codec')
    op.drop_column('agent_config', 'noise_suppression_level')
