"""Initial migration with all existing tables

Revision ID: c9f05c1b0a49
Revises: 
Create Date: 2026-01-06 17:13:44.410701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9f05c1b0a49'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    """Create all existing tables with their current schema (Idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create calls table
    if 'calls' not in tables:
        op.create_table(
            'calls',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('session_id', sa.String(), nullable=True),
            sa.Column('start_time', sa.DateTime(), nullable=True),
            sa.Column('end_time', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(), nullable=True),
            sa.Column('client_type', sa.String(), nullable=True),
            sa.Column('extracted_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_calls_id'), 'calls', ['id'], unique=False)
        op.create_index(op.f('ix_calls_session_id'), 'calls', ['session_id'], unique=True)
    
    # Create transcripts table
    if 'transcripts' not in tables:
        op.create_table(
            'transcripts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('call_id', sa.Integer(), nullable=True),
            sa.Column('role', sa.String(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_transcripts_id'), 'transcripts', ['id'], unique=False)
    
    # Create agent_configs table
    if 'agent_configs' not in tables:
        op.create_table(
            'agent_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            
            sa.Column('stt_provider', sa.String(), nullable=True),
            sa.Column('stt_language', sa.String(), nullable=True),
            sa.Column('llm_provider', sa.String(), nullable=True),
            sa.Column('llm_model', sa.String(), nullable=True),
            sa.Column('extraction_model', sa.String(), nullable=True),
            sa.Column('interruption_threshold', sa.Integer(), nullable=True),
            sa.Column('interruption_threshold_phone', sa.Integer(), nullable=True),
            sa.Column('tts_provider', sa.String(), nullable=True),

            # STT Advanced (Missing)
            sa.Column('stt_model', sa.String(), nullable=True),
            sa.Column('stt_keywords', sa.JSON(), nullable=True),
            sa.Column('stt_silence_timeout', sa.Integer(), nullable=True),
            sa.Column('stt_utterance_end_strategy', sa.String(), nullable=True),
            sa.Column('stt_punctuation', sa.Boolean(), nullable=True),
            sa.Column('stt_profanity_filter', sa.Boolean(), nullable=True),
            sa.Column('stt_smart_formatting', sa.Boolean(), nullable=True),
            sa.Column('stt_diarization', sa.Boolean(), nullable=True),
            sa.Column('stt_multilingual', sa.Boolean(), nullable=True),
            
            # Parameters
            sa.Column('system_prompt', sa.Text(), nullable=True),
            sa.Column('voice_name', sa.String(), nullable=True),
            sa.Column('voice_style', sa.String(), nullable=True),
            sa.Column('voice_speed', sa.Float(), nullable=True),
            sa.Column('voice_speed_phone', sa.Float(), nullable=True),
            sa.Column('temperature', sa.Float(), nullable=True),
            sa.Column('background_sound', sa.String(), nullable=True),

            # Voice Expression (Azure)
            sa.Column('voice_pitch', sa.Integer(), nullable=True),
            sa.Column('voice_volume', sa.Integer(), nullable=True),
            sa.Column('voice_style_degree', sa.Float(), nullable=True),
            
            # ElevenLabs
            sa.Column('voice_stability', sa.Float(), nullable=True),
            sa.Column('voice_similarity_boost', sa.Float(), nullable=True),
            sa.Column('voice_style_exaggeration', sa.Float(), nullable=True),
            sa.Column('voice_speaker_boost', sa.Boolean(), nullable=True),
            sa.Column('voice_multilingual', sa.Boolean(), nullable=True),

            # Technical TTS
            sa.Column('tts_latency_optimization', sa.Integer(), nullable=True),
            sa.Column('tts_output_format', sa.String(), nullable=True),

            # Humanization
            sa.Column('voice_filler_injection', sa.Boolean(), nullable=True),
            sa.Column('voice_backchanneling', sa.Boolean(), nullable=True),
            sa.Column('text_normalization_rule', sa.String(), nullable=True),
            sa.Column('pronunciation_dictionary', sa.JSON(), nullable=True),
            
            # Flow Control
            sa.Column('idle_timeout', sa.Float(), nullable=True),
            sa.Column('idle_message', sa.String(), nullable=True),
            sa.Column('inactivity_max_retries', sa.Integer(), nullable=True),
            sa.Column('max_duration', sa.Integer(), nullable=True),

            # Advanced LLM & Style (Missing in original export)
            sa.Column('context_window', sa.Integer(), nullable=True),
            sa.Column('tool_choice', sa.String(), nullable=True),
            sa.Column('response_length', sa.String(), nullable=True),
            sa.Column('conversation_tone', sa.String(), nullable=True),
            sa.Column('conversation_formality', sa.String(), nullable=True),
            sa.Column('conversation_pacing', sa.String(), nullable=True),
            
            # VAPI Stage 1
            sa.Column('first_message', sa.String(), nullable=True),
            sa.Column('first_message_mode', sa.String(), nullable=True),
            sa.Column('max_tokens', sa.Integer(), nullable=True),
            
            # Phone Profile (Twilio)
            sa.Column('stt_provider_phone', sa.String(), nullable=True),
            sa.Column('stt_language_phone', sa.String(), nullable=True),
            
            # STT Advanced Phone
            sa.Column('stt_model_phone', sa.String(), nullable=True),
            sa.Column('stt_keywords_phone', sa.JSON(), nullable=True),
            sa.Column('stt_silence_timeout_phone', sa.Integer(), nullable=True),
            sa.Column('stt_utterance_end_strategy_phone', sa.String(), nullable=True),
            sa.Column('stt_punctuation_phone', sa.Boolean(), nullable=True),
            sa.Column('stt_profanity_filter_phone', sa.Boolean(), nullable=True),
            sa.Column('stt_smart_formatting_phone', sa.Boolean(), nullable=True),
            sa.Column('stt_diarization_phone', sa.Boolean(), nullable=True),
            sa.Column('stt_multilingual_phone', sa.Boolean(), nullable=True),

            sa.Column('llm_provider_phone', sa.String(), nullable=True),
            sa.Column('llm_model_phone', sa.String(), nullable=True),
            sa.Column('system_prompt_phone', sa.Text(), nullable=True),
            sa.Column('voice_name_phone', sa.String(), nullable=True),
            sa.Column('voice_style_phone', sa.String(), nullable=True),
            sa.Column('temperature_phone', sa.Float(), nullable=True),
            sa.Column('first_message_phone', sa.String(), nullable=True),
            sa.Column('first_message_mode_phone', sa.String(), nullable=True),
            sa.Column('max_tokens_phone', sa.Integer(), nullable=True),
            sa.Column('initial_silence_timeout_ms_phone', sa.Integer(), nullable=True),
            sa.Column('input_min_characters_phone', sa.Integer(), nullable=True),
            sa.Column('enable_denoising_phone', sa.Boolean(), nullable=True),
            sa.Column('extra_settings_phone', postgresql.JSON(astext_type=sa.Text()), nullable=True),

            # Advanced LLM & Style Phone (Missing in original export)
            sa.Column('context_window_phone', sa.Integer(), nullable=True),
            sa.Column('tool_choice_phone', sa.String(), nullable=True),
            sa.Column('response_length_phone', sa.String(), nullable=True),
            sa.Column('conversation_tone_phone', sa.String(), nullable=True),
            sa.Column('conversation_formality_phone', sa.String(), nullable=True),
            sa.Column('conversation_pacing_phone', sa.String(), nullable=True),
            
            # Voice Expression Phone
            sa.Column('voice_pitch_phone', sa.Integer(), nullable=True),
            sa.Column('voice_volume_phone', sa.Integer(), nullable=True),
            sa.Column('voice_style_degree_phone', sa.Float(), nullable=True),
            
            # ElevenLabs Phone
            sa.Column('voice_stability_phone', sa.Float(), nullable=True),
            sa.Column('voice_similarity_boost_phone', sa.Float(), nullable=True),
            sa.Column('voice_style_exaggeration_phone', sa.Float(), nullable=True),
            sa.Column('voice_speaker_boost_phone', sa.Boolean(), nullable=True),
            sa.Column('voice_multilingual_phone', sa.Boolean(), nullable=True),

            # Technical TTS Phone
            sa.Column('tts_latency_optimization_phone', sa.Integer(), nullable=True),
            sa.Column('tts_output_format_phone', sa.String(), nullable=True),

            # Humanization Phone
            sa.Column('voice_filler_injection_phone', sa.Boolean(), nullable=True),
            sa.Column('voice_backchanneling_phone', sa.Boolean(), nullable=True),
            sa.Column('text_normalization_rule_phone', sa.String(), nullable=True),
            sa.Column('pronunciation_dictionary_phone', sa.JSON(), nullable=True),

            # Twilio Specific
            sa.Column('twilio_machine_detection', sa.String(), nullable=True),
            sa.Column('twilio_record', sa.Boolean(), nullable=True),
            sa.Column('twilio_recording_channels', sa.String(), nullable=True),
            sa.Column('twilio_trim_silence', sa.Boolean(), nullable=True),
            
            # VAPI Stage 2
            sa.Column('voice_id_manual', sa.String(), nullable=True),
            sa.Column('background_sound_url', sa.String(), nullable=True),
            sa.Column('input_min_characters', sa.Integer(), nullable=True),
            sa.Column('hallucination_blacklist', sa.String(), nullable=True),
            sa.Column('hallucination_blacklist_phone', sa.String(), nullable=True),
            sa.Column('voice_pacing_ms', sa.Integer(), nullable=True),
            sa.Column('voice_pacing_ms_phone', sa.Integer(), nullable=True),
            sa.Column('punctuation_boundaries', sa.String(), nullable=True),
            sa.Column('silence_timeout_ms', sa.Integer(), nullable=True),
            sa.Column('silence_timeout_ms_phone', sa.Integer(), nullable=True),
            sa.Column('segmentation_max_time', sa.Integer(), nullable=True),
            sa.Column('segmentation_strategy', sa.String(), nullable=True),
            sa.Column('enable_denoising', sa.Boolean(), nullable=True),
            sa.Column('initial_silence_timeout_ms', sa.Integer(), nullable=True),
            
            # VAD Sensitivity
            sa.Column('voice_sensitivity', sa.Integer(), nullable=True),
            sa.Column('voice_sensitivity_phone', sa.Integer(), nullable=True),
            
            # Telnyx Profile
            sa.Column('stt_provider_telnyx', sa.String(), nullable=True),
            sa.Column('stt_language_telnyx', sa.String(), nullable=True),
            
            # STT Advanced Telnyx
            sa.Column('stt_model_telnyx', sa.String(), nullable=True),
            sa.Column('stt_keywords_telnyx', sa.JSON(), nullable=True),
            sa.Column('stt_silence_timeout_telnyx', sa.Integer(), nullable=True),
            sa.Column('stt_utterance_end_strategy_telnyx', sa.String(), nullable=True),
            sa.Column('stt_punctuation_telnyx', sa.Boolean(), nullable=True),
            sa.Column('stt_profanity_filter_telnyx', sa.Boolean(), nullable=True),
            sa.Column('stt_smart_formatting_telnyx', sa.Boolean(), nullable=True),
            sa.Column('stt_diarization_telnyx', sa.Boolean(), nullable=True),
            sa.Column('stt_multilingual_telnyx', sa.Boolean(), nullable=True),

            sa.Column('llm_provider_telnyx', sa.String(), nullable=True),
            sa.Column('llm_model_telnyx', sa.String(), nullable=True),
            sa.Column('system_prompt_telnyx', sa.Text(), nullable=True),
            sa.Column('voice_name_telnyx', sa.String(), nullable=True),
            sa.Column('voice_style_telnyx', sa.String(), nullable=True),
            sa.Column('temperature_telnyx', sa.Float(), nullable=True),
            sa.Column('first_message_telnyx', sa.String(), nullable=True),
            sa.Column('first_message_mode_telnyx', sa.String(), nullable=True),
            sa.Column('max_tokens_telnyx', sa.Integer(), nullable=True),
            sa.Column('initial_silence_timeout_ms_telnyx', sa.Integer(), nullable=True),
            sa.Column('input_min_characters_telnyx', sa.Integer(), nullable=True),
            sa.Column('enable_denoising_telnyx', sa.Boolean(), nullable=True),
            sa.Column('voice_pacing_ms_telnyx', sa.Integer(), nullable=True),
            sa.Column('silence_timeout_ms_telnyx', sa.Integer(), nullable=True),
            sa.Column('interruption_threshold_telnyx', sa.Integer(), nullable=True),
            sa.Column('hallucination_blacklist_telnyx', sa.String(), nullable=True),
            sa.Column('voice_speed_telnyx', sa.Float(), nullable=True),
            sa.Column('voice_sensitivity_telnyx', sa.Integer(), nullable=True),
            sa.Column('enable_krisp_telnyx', sa.Boolean(), nullable=True),
            sa.Column('enable_vad_telnyx', sa.Boolean(), nullable=True),
            sa.Column('idle_timeout_telnyx', sa.Float(), nullable=True),
            sa.Column('max_duration_telnyx', sa.Integer(), nullable=True),
            sa.Column('idle_message_telnyx', sa.String(), nullable=True),
            sa.Column('enable_recording_telnyx', sa.Boolean(), nullable=True),
            sa.Column('amd_config_telnyx', sa.String(), nullable=True),
            
            # Advanced LLM & Style Telnyx (Missing in original export)
            sa.Column('context_window_telnyx', sa.Integer(), nullable=True),
            sa.Column('tool_choice_telnyx', sa.String(), nullable=True),
            sa.Column('response_length_telnyx', sa.String(), nullable=True),
            sa.Column('conversation_tone_telnyx', sa.String(), nullable=True),
            sa.Column('conversation_formality_telnyx', sa.String(), nullable=True),
            sa.Column('conversation_pacing_telnyx', sa.String(), nullable=True),

            # Voice Expression Telnyx
            sa.Column('voice_pitch_telnyx', sa.Integer(), nullable=True),
            sa.Column('voice_volume_telnyx', sa.Integer(), nullable=True),
            sa.Column('voice_style_degree_telnyx', sa.Float(), nullable=True),
            
            # ElevenLabs Telnyx
            sa.Column('voice_stability_telnyx', sa.Float(), nullable=True),
            sa.Column('voice_similarity_boost_telnyx', sa.Float(), nullable=True),
            sa.Column('voice_style_exaggeration_telnyx', sa.Float(), nullable=True),
            sa.Column('voice_speaker_boost_telnyx', sa.Boolean(), nullable=True),
            sa.Column('voice_multilingual_telnyx', sa.Boolean(), nullable=True),

            # Technical TTS Telnyx
            sa.Column('tts_latency_optimization_telnyx', sa.Integer(), nullable=True),
            sa.Column('tts_output_format_telnyx', sa.String(), nullable=True),

            # Humanization Telnyx
            sa.Column('voice_filler_injection_telnyx', sa.Boolean(), nullable=True),
            sa.Column('voice_backchanneling_telnyx', sa.Boolean(), nullable=True),
            sa.Column('text_normalization_rule_telnyx', sa.String(), nullable=True),
            sa.Column('pronunciation_dictionary_telnyx', sa.JSON(), nullable=True),

            # Call Control
            sa.Column('enable_end_call', sa.Boolean(), nullable=True),
            sa.Column('enable_dial_keypad', sa.Boolean(), nullable=True),
            sa.Column('transfer_phone_number', sa.String(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_agent_configs_id'), 'agent_configs', ['id'], unique=False)
        op.create_index(op.f('ix_agent_configs_name'), 'agent_configs', ['name'], unique=True)


def downgrade() -> None:
    """Drop all tables."""
    # Note: Downgrade also needs to be careful or we just drop everything as expected
    op.drop_index(op.f('ix_agent_configs_name'), table_name='agent_configs')
    op.drop_index(op.f('ix_agent_configs_id'), table_name='agent_configs')
    op.drop_table('agent_configs')
    op.drop_index(op.f('ix_transcripts_id'), table_name='transcripts')
    op.drop_table('transcripts')
    op.drop_index(op.f('ix_calls_session_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_id'), table_name='calls')
    op.drop_table('calls')

