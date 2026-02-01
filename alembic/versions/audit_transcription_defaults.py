"""audit_transcription_defaults

Revision ID: audit_transcription_defaults
Revises: audit_voice_defaults
Create Date: 2026-02-01 01:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'audit_transcription_defaults'
down_revision: Union[str, None] = 'audit_voice_defaults'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --------------------------------------------------------------------------
    # TRANSCRIPTION TAB AUDIT & DEFAULTS
    # Enforcing optimal STT (Azure) and VAD settings
    # --------------------------------------------------------------------------

    # 1. Browser Profile
    op.execute("""
        UPDATE agent_configs
        SET 
            stt_provider = 'azure',
            stt_language = 'es-MX',
            vad_threshold = 0.5,
            voice_sensitivity = 500,
            enable_denoising = true,
            stt_punctuation = true,
            stt_smart_formatting = true
        WHERE name = 'default';
    """)

    # 2. Phone Profile (Twilio)
    op.execute("""
        UPDATE agent_configs
        SET 
            stt_provider_phone = 'azure',
            stt_language_phone = 'es-MX',
            vad_threshold_phone = 0.5,
            voice_sensitivity_phone = 3000,
            enable_denoising_phone = true,
            stt_punctuation_phone = true,
            stt_smart_formatting_phone = true
        WHERE name = 'default';
    """)

    # 3. Telnyx Profile
    op.execute("""
        UPDATE agent_configs
        SET 
            stt_provider_telnyx = 'azure',
            stt_language_telnyx = 'es-MX',
            vad_threshold_telnyx = 0.5,
            voice_sensitivity_telnyx = 3000,
            enable_denoising_telnyx = true,
            stt_punctuation_telnyx = true,
            stt_smart_formatting_telnyx = true,
            noise_suppression_level_telnyx = 'balanced',
            enable_vad_telnyx = true
        WHERE name = 'default';
    """)


def downgrade() -> None:
    pass
