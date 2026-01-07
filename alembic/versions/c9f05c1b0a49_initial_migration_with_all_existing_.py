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
    """Create all existing tables with their current schema."""
    
    # Create calls table
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
    
    # Create agent_configs table with ALL current columns
    op.create_table(
        'agent_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        
        # Providers
        sa.Column('stt_provider', sa.String(), nullable=True),
        sa.Column('stt_language', sa.String(), nullable=True),
        sa.Column('llm_provider', sa.String(), nullable=True),
        sa.Column('llm_model', sa.String(), nullable=True),
        sa.Column('extraction_model', sa.String(), nullable=True),
        sa.Column('interruption_threshold', sa.Integer(), nullable=True),
        sa.Column('interruption_threshold_phone', sa.Integer(), nullable=True),
        sa.Column('tts_provider', sa.String(), nullable=True),
        
        # Parameters
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('voice_name', sa.String(), nullable=True),
        sa.Column('voice_style', sa.String(), nullable=True),
        sa.Column('voice_speed', sa.Float(), nullable=True),
        sa.Column('voice_speed_phone', sa.Float(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('background_sound', sa.String(), nullable=True),
        
        # Flow Control
        sa.Column('idle_timeout', sa.Float(), nullable=True),
        sa.Column('idle_message', sa.String(), nullable=True),
        sa.Column('inactivity_max_retries', sa.Integer(), nullable=True),
        sa.Column('max_duration', sa.Integer(), nullable=True),
        
        # VAPI Stage 1
        sa.Column('first_message', sa.String(), nullable=True),
        sa.Column('first_message_mode', sa.String(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        
        # Phone Profile (Twilio)
        sa.Column('stt_provider_phone', sa.String(), nullable=True),
        sa.Column('stt_language_phone', sa.String(), nullable=True),
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
    op.drop_index(op.f('ix_agent_configs_name'), table_name='agent_configs')
    op.drop_index(op.f('ix_agent_configs_id'), table_name='agent_configs')
    op.drop_table('agent_configs')
    op.drop_index(op.f('ix_transcripts_id'), table_name='transcripts')
    op.drop_table('transcripts')
    op.drop_index(op.f('ix_calls_session_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_id'), table_name='calls')
    op.drop_table('calls')
