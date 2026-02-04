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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]
    
    # -------------------------------------------------------------------------
    # 1. BROWSER PROFILE (Base)
    # -------------------------------------------------------------------------
    # ElevenLabs Specifics
    if 'voice_stability' not in columns:
        op.add_column('agent_configs', sa.Column('voice_stability', sa.Float(), nullable=False, server_default='0.5'))
    if 'voice_similarity_boost' not in columns:
        op.add_column('agent_configs', sa.Column('voice_similarity_boost', sa.Float(), nullable=False, server_default='0.75'))
    if 'voice_style_exaggeration' not in columns:
        op.add_column('agent_configs', sa.Column('voice_style_exaggeration', sa.Float(), nullable=False, server_default='0.0'))
    if 'voice_speaker_boost' not in columns:
        op.add_column('agent_configs', sa.Column('voice_speaker_boost', sa.Boolean(), nullable=False, server_default='true'))
    if 'voice_multilingual' not in columns:
        op.add_column('agent_configs', sa.Column('voice_multilingual', sa.Boolean(), nullable=False, server_default='true'))
    
    # Technical Settings
    if 'tts_latency_optimization' not in columns:
        op.add_column('agent_configs', sa.Column('tts_latency_optimization', sa.Integer(), nullable=False, server_default='0'))
    if 'tts_output_format' not in columns:
        op.add_column('agent_configs', sa.Column('tts_output_format', sa.String(), nullable=False, server_default='pcm_16000'))
    
    # Humanization
    if 'voice_filler_injection' not in columns:
        op.add_column('agent_configs', sa.Column('voice_filler_injection', sa.Boolean(), nullable=False, server_default='false'))
    if 'voice_backchanneling' not in columns:
        op.add_column('agent_configs', sa.Column('voice_backchanneling', sa.Boolean(), nullable=False, server_default='false'))
    if 'text_normalization_rule' not in columns:
        op.add_column('agent_configs', sa.Column('text_normalization_rule', sa.String(), nullable=False, server_default='auto'))
    if 'pronunciation_dictionary' not in columns:
        op.add_column('agent_configs', sa.Column('pronunciation_dictionary', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # -------------------------------------------------------------------------
    # 2. TWILIO PROFILE (_phone)
    # -------------------------------------------------------------------------
    if 'voice_stability_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_stability_phone', sa.Float(), nullable=False, server_default='0.5'))
    if 'voice_similarity_boost_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_similarity_boost_phone', sa.Float(), nullable=False, server_default='0.75'))
    if 'voice_style_exaggeration_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_style_exaggeration_phone', sa.Float(), nullable=False, server_default='0.0'))
    if 'voice_speaker_boost_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_speaker_boost_phone', sa.Boolean(), nullable=False, server_default='true'))
    if 'voice_multilingual_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_multilingual_phone', sa.Boolean(), nullable=False, server_default='true'))
    
    if 'tts_latency_optimization_phone' not in columns:
        op.add_column('agent_configs', sa.Column('tts_latency_optimization_phone', sa.Integer(), nullable=False, server_default='0'))
    if 'tts_output_format_phone' not in columns:
        op.add_column('agent_configs', sa.Column('tts_output_format_phone', sa.String(), nullable=False, server_default='pcm_8000')) # Phone default
    
    if 'voice_filler_injection_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_filler_injection_phone', sa.Boolean(), nullable=False, server_default='false'))
    if 'voice_backchanneling_phone' not in columns:
        op.add_column('agent_configs', sa.Column('voice_backchanneling_phone', sa.Boolean(), nullable=False, server_default='false'))
    if 'text_normalization_rule_phone' not in columns:
        op.add_column('agent_configs', sa.Column('text_normalization_rule_phone', sa.String(), nullable=False, server_default='auto'))
    if 'pronunciation_dictionary_phone' not in columns:
        op.add_column('agent_configs', sa.Column('pronunciation_dictionary_phone', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # -------------------------------------------------------------------------
    # 3. TELNYX PROFILE (_telnyx)
    # -------------------------------------------------------------------------
    if 'voice_stability_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_stability_telnyx', sa.Float(), nullable=False, server_default='0.5'))
    if 'voice_similarity_boost_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_similarity_boost_telnyx', sa.Float(), nullable=False, server_default='0.75'))
    if 'voice_style_exaggeration_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_style_exaggeration_telnyx', sa.Float(), nullable=False, server_default='0.0'))
    if 'voice_speaker_boost_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_speaker_boost_telnyx', sa.Boolean(), nullable=False, server_default='true'))
    if 'voice_multilingual_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_multilingual_telnyx', sa.Boolean(), nullable=False, server_default='true'))
    
    if 'tts_latency_optimization_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('tts_latency_optimization_telnyx', sa.Integer(), nullable=False, server_default='0'))
    if 'tts_output_format_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('tts_output_format_telnyx', sa.String(), nullable=False, server_default='pcm_8000')) # Phone default
    
    if 'voice_filler_injection_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_filler_injection_telnyx', sa.Boolean(), nullable=False, server_default='false'))
    if 'voice_backchanneling_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('voice_backchanneling_telnyx', sa.Boolean(), nullable=False, server_default='false'))
    if 'text_normalization_rule_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('text_normalization_rule_telnyx', sa.String(), nullable=False, server_default='auto'))
    if 'pronunciation_dictionary_telnyx' not in columns:
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
