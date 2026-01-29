"""add_tts_voice_controls_v2

Revision ID: tts_controls_v2
Revises: llm_controls_v1
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'tts_controls_v2'
down_revision = 'llm_controls_v1'
branch_labels = None
depends_on = None


def upgrade():
    """Add TTS & Voice Control fields (ElevenLabs, Humanization, Tech) x 3 Profiles."""
    
    # -------------------------------------------------------------------------
    # 1. BROWSER PROFILE (Base)
    # -------------------------------------------------------------------------
    # ElevenLabs Specifics
    op.add_column('agent_configs', sa.Column('voice_stability', sa.Float(), nullable=False, server_default='0.5'))
    op.add_column('agent_configs', sa.Column('voice_similarity_boost', sa.Float(), nullable=False, server_default='0.75'))
    op.add_column('agent_configs', sa.Column('voice_style_exaggeration', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('voice_speaker_boost', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('agent_configs', sa.Column('voice_multilingual', sa.Boolean(), nullable=False, server_default='true'))
    
    # Technical Settings
    op.add_column('agent_configs', sa.Column('tts_latency_optimization', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('agent_configs', sa.Column('tts_output_format', sa.String(), nullable=False, server_default='pcm_16000'))
    
    # Humanization
    op.add_column('agent_configs', sa.Column('voice_filler_injection', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('voice_backchanneling', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('text_normalization_rule', sa.String(), nullable=False, server_default='auto'))
    op.add_column('agent_configs', sa.Column('pronunciation_dictionary', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # -------------------------------------------------------------------------
    # 2. TWILIO PROFILE (_phone)
    # -------------------------------------------------------------------------
    op.add_column('agent_configs', sa.Column('voice_stability_phone', sa.Float(), nullable=False, server_default='0.5'))
    op.add_column('agent_configs', sa.Column('voice_similarity_boost_phone', sa.Float(), nullable=False, server_default='0.75'))
    op.add_column('agent_configs', sa.Column('voice_style_exaggeration_phone', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('voice_speaker_boost_phone', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('agent_configs', sa.Column('voice_multilingual_phone', sa.Boolean(), nullable=False, server_default='true'))
    
    op.add_column('agent_configs', sa.Column('tts_latency_optimization_phone', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('agent_configs', sa.Column('tts_output_format_phone', sa.String(), nullable=False, server_default='pcm_8000')) # Phone default
    
    op.add_column('agent_configs', sa.Column('voice_filler_injection_phone', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('voice_backchanneling_phone', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('text_normalization_rule_phone', sa.String(), nullable=False, server_default='auto'))
    op.add_column('agent_configs', sa.Column('pronunciation_dictionary_phone', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # -------------------------------------------------------------------------
    # 3. TELNYX PROFILE (_telnyx)
    # -------------------------------------------------------------------------
    op.add_column('agent_configs', sa.Column('voice_stability_telnyx', sa.Float(), nullable=False, server_default='0.5'))
    op.add_column('agent_configs', sa.Column('voice_similarity_boost_telnyx', sa.Float(), nullable=False, server_default='0.75'))
    op.add_column('agent_configs', sa.Column('voice_style_exaggeration_telnyx', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('voice_speaker_boost_telnyx', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('agent_configs', sa.Column('voice_multilingual_telnyx', sa.Boolean(), nullable=False, server_default='true'))
    
    op.add_column('agent_configs', sa.Column('tts_latency_optimization_telnyx', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('agent_configs', sa.Column('tts_output_format_telnyx', sa.String(), nullable=False, server_default='pcm_8000')) # Phone default
    
    op.add_column('agent_configs', sa.Column('voice_filler_injection_telnyx', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('voice_backchanneling_telnyx', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('text_normalization_rule_telnyx', sa.String(), nullable=False, server_default='auto'))
    op.add_column('agent_configs', sa.Column('pronunciation_dictionary_telnyx', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    """Remove all TTS control fields."""
    
    # -------------------------------------------------------------------------
    # BROWSER
    # -------------------------------------------------------------------------
    op.drop_column('agent_configs', 'pronunciation_dictionary')
    op.drop_column('agent_configs', 'text_normalization_rule')
    op.drop_column('agent_configs', 'voice_backchanneling')
    op.drop_column('agent_configs', 'voice_filler_injection')
    op.drop_column('agent_configs', 'tts_output_format')
    op.drop_column('agent_configs', 'tts_latency_optimization')
    op.drop_column('agent_configs', 'voice_multilingual')
    op.drop_column('agent_configs', 'voice_speaker_boost')
    op.drop_column('agent_configs', 'voice_style_exaggeration')
    op.drop_column('agent_configs', 'voice_similarity_boost')
    op.drop_column('agent_configs', 'voice_stability')
    
    # -------------------------------------------------------------------------
    # TWILIO
    # -------------------------------------------------------------------------
    op.drop_column('agent_configs', 'pronunciation_dictionary_phone')
    op.drop_column('agent_configs', 'text_normalization_rule_phone')
    op.drop_column('agent_configs', 'voice_backchanneling_phone')
    op.drop_column('agent_configs', 'voice_filler_injection_phone')
    op.drop_column('agent_configs', 'tts_output_format_phone')
    op.drop_column('agent_configs', 'tts_latency_optimization_phone')
    op.drop_column('agent_configs', 'voice_multilingual_phone')
    op.drop_column('agent_configs', 'voice_speaker_boost_phone')
    op.drop_column('agent_configs', 'voice_style_exaggeration_phone')
    op.drop_column('agent_configs', 'voice_similarity_boost_phone')
    op.drop_column('agent_configs', 'voice_stability_phone')

    # -------------------------------------------------------------------------
    # TELNYX
    # -------------------------------------------------------------------------
    op.drop_column('agent_configs', 'pronunciation_dictionary_telnyx')
    op.drop_column('agent_configs', 'text_normalization_rule_telnyx')
    op.drop_column('agent_configs', 'voice_backchanneling_telnyx')
    op.drop_column('agent_configs', 'voice_filler_injection_telnyx')
    op.drop_column('agent_configs', 'tts_output_format_telnyx')
    op.drop_column('agent_configs', 'tts_latency_optimization_telnyx')
    op.drop_column('agent_configs', 'voice_multilingual_telnyx')
    op.drop_column('agent_configs', 'voice_speaker_boost_telnyx')
    op.drop_column('agent_configs', 'voice_style_exaggeration_telnyx')
    op.drop_column('agent_configs', 'voice_similarity_boost_telnyx')
    op.drop_column('agent_configs', 'voice_stability_telnyx')
