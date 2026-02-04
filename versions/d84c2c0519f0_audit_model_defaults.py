"""audit_model_defaults

Revision ID: d84c2c0519f0
Revises: bbbe703ac987
Create Date: 2026-02-01 00:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd84c2c0519f0'
down_revision: Union[str, None] = 'bbbe703ac987'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --------------------------------------------------------------------------
    # MODEL TAB AUDIT & DEFAULTS
    # Enforcing optimal defaults for LLM interactions across all profiles
    # --------------------------------------------------------------------------

    # 1. BROWSER PROFILE (Default)
    op.execute("""
        UPDATE agent_configs
        SET 
            llm_provider = 'groq',
            llm_model = 'llama-3.3-70b-versatile',
            temperature = 0.7,
            max_tokens = 250,
            context_window = 10,
            response_length = 'short',
            conversation_tone = 'warm',
            conversation_formality = 'semi_formal',
            conversation_pacing = 'moderate',
            tool_choice = 'auto'
        WHERE name = 'default';
    """)

    # 2. PHONE PROFILE (Twilio)
    op.execute("""
        UPDATE agent_configs
        SET 
            llm_provider_phone = 'groq',
            llm_model_phone = 'llama-3.3-70b-versatile',
            temperature_phone = 0.7,
            max_tokens_phone = 250,
            context_window_phone = 10,
            response_length_phone = 'short',
            conversation_tone_phone = 'warm',
            conversation_formality_phone = 'semi_formal',
            conversation_pacing_phone = 'moderate',
            tool_choice_phone = 'auto'
        WHERE name = 'default';
    """)

    # 3. TELNYX PROFILE
    op.execute("""
        UPDATE agent_configs
        SET 
            llm_provider_telnyx = 'groq',
            llm_model_telnyx = 'llama-3.3-70b-versatile',
            temperature_telnyx = 0.7,
            max_tokens_telnyx = 250,
            context_window_telnyx = 10,
            response_length_telnyx = 'short',
            conversation_tone_telnyx = 'warm',
            conversation_formality_telnyx = 'semi_formal',
            conversation_pacing_telnyx = 'moderate',
            tool_choice_telnyx = 'auto'
        WHERE name = 'default';
    """)


def downgrade() -> None:
    # No reversion logic needed for audit verification
    pass
