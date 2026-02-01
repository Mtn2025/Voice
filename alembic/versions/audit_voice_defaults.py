"""audit_voice_defaults

Revision ID: audit_voice_defaults
Revises: merge_heads_20260201
Create Date: 2026-02-01 01:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'audit_voice_defaults'
down_revision: Union[str, None] = 'merge_heads_20260201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --------------------------------------------------------------------------
    # VOICE TAB AUDIT & DEFAULTS
    # Fixes "Empty Language" issue and enforces standard Spanish voice settings
    # --------------------------------------------------------------------------

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    # 1. Ensure Columns Exist (Safety Check)
    if 'voice_language' not in columns:
        op.add_column('agent_configs', sa.Column('voice_language', sa.String(), server_default='es-MX'))
    if 'voice_language_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_language_phone', sa.String(), server_default='es-MX'))
    if 'voice_language_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_language_telnyx', sa.String(), server_default='es-MX'))

    # 2. DATA REPAIR: Fix Empty Language
    op.execute("UPDATE agent_configs SET voice_language = 'es-MX' WHERE voice_language IS NULL OR voice_language = ''")
    op.execute("UPDATE agent_configs SET voice_language_phone = 'es-MX' WHERE voice_language_phone IS NULL OR voice_language_phone = ''")
    op.execute("UPDATE agent_configs SET voice_language_telnyx = 'es-MX' WHERE voice_language_telnyx IS NULL OR voice_language_telnyx = ''")

    # 3. SET OPTIMAL DEFAULTS FOR VOICE TAB
    
    # Browser Profile
    op.execute("""
        UPDATE agent_configs
        SET 
            tts_provider = 'azure',
            voice_name = 'es-MX-DaliaNeural',
            voice_style = 'default',
            voice_speed = 1.0,
            voice_pitch = 0,
            voice_volume = 100,
            voice_style_degree = 1.0,
            voice_stability = 0.5,
            voice_similarity_boost = 0.75
        WHERE name = 'default';
    """)

    # Phone Profile (Slower speed for telephony)
    op.execute("""
        UPDATE agent_configs
        SET 
            tts_provider_phone = 'azure',
            voice_name_phone = 'es-MX-DaliaNeural',
            voice_style_phone = 'default',
            voice_speed_phone = 0.9,
            voice_pitch_phone = 0,
            voice_volume_phone = 100,
            voice_style_degree_phone = 1.0
        WHERE name = 'default';
    """)

    # Telnyx Profile (Slower speed, matching Phone)
    op.execute("""
        UPDATE agent_configs
        SET 
            tts_provider_telnyx = 'azure',
            voice_name_telnyx = 'es-MX-DaliaNeural',
            voice_style_telnyx = 'default',
            voice_speed_telnyx = 0.9,
            voice_pitch_telnyx = 0,
            voice_volume_telnyx = 100,
            voice_style_degree_telnyx = 1.0
        WHERE name = 'default';
    """)


def downgrade() -> None:
    pass
