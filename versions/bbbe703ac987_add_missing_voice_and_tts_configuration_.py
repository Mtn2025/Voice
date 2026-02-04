"""add missing voice and tts configuration fields

Revision ID: bbbe703ac987
Revises: 2a4b5c6d7e8f
Create Date: 2026-01-10 17:25:56.482712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbbe703ac987'
down_revision: Union[str, Sequence[str], None] = '2a4b5c6d7e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing voice_language and TTS configuration fields."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    # Add voice_language to base profile
    if 'voice_language' not in columns:
        op.add_column('agent_configs', sa.Column('voice_language', sa.String(), nullable=True, server_default='es-MX'))
    
    # Add missing TTS/voice fields for Phone profile  
    if 'tts_provider_phone' not in columns:
        op.add_column('agent_configs', sa.Column('tts_provider_phone', sa.String(), nullable=True, server_default='azure'))
    if 'voice_language_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_language_phone', sa.String(), nullable=True, server_default='es-MX'))
    if 'background_sound_phone' not in columns:
        op.add_column('agent_configs', sa.Column('background_sound_phone', sa.String(), nullable=True, server_default='none'))
    
    # Add missing TTS/voice fields for Telnyx profile
    if 'tts_provider_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('tts_provider_telnyx', sa.String(), nullable=True, server_default='azure'))
    if 'voice_language_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_language_telnyx', sa.String(), nullable=True, server_default='es-MX'))
    if 'background_sound_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('background_sound_telnyx', sa.String(), nullable=True, server_default='none'))
    if 'background_sound_url_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('background_sound_url_telnyx', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove the added columns."""
    op.drop_column('agent_configs', 'background_sound_url_telnyx')
    op.drop_column('agent_configs', 'background_sound_telnyx')
    op.drop_column('agent_configs', 'voice_language_telnyx')
    op.drop_column('agent_configs', 'tts_provider_telnyx')
    op.drop_column('agent_configs', 'background_sound_phone')
    op.drop_column('agent_configs', 'voice_language_phone')
    op.drop_column('agent_configs', 'tts_provider_phone')
    op.drop_column('agent_configs', 'voice_language')
