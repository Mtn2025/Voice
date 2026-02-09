"""fix_schema_drift

Revision ID: 103d76d39916
Revises: 008_features_viii
Create Date: 2026-02-03 23:21:59.117359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '103d76d39916'
down_revision: Union[str, Sequence[str], None] = '008_features_viii'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    current_columns = {c['name'] for c in inspector.get_columns('agent_configs')}

    # List of columns to add (name, type)
    new_columns = [
        ('barge_in_enabled', sa.Boolean()),
        ('interruption_sensitivity', sa.Float()),
        ('interruption_phrases', sa.JSON()),
        ('barge_in_enabled_phone', sa.Boolean()),
        ('interruption_sensitivity_phone', sa.Float()),
        ('interruption_phrases_phone', sa.JSON()),
        ('barge_in_enabled_telnyx', sa.Boolean()),
        ('interruption_sensitivity_telnyx', sa.Float()),
        ('interruption_phrases_telnyx', sa.JSON()),
        ('voicemail_detection_enabled', sa.Boolean()),
        ('voicemail_message', sa.Text()),
        ('machine_detection_sensitivity', sa.Float()),
        ('voicemail_detection_enabled_phone', sa.Boolean()),
        ('voicemail_message_phone', sa.Text()),
        ('machine_detection_sensitivity_phone', sa.Float()),
        ('voicemail_detection_enabled_telnyx', sa.Boolean()),
        ('voicemail_message_telnyx', sa.Text()),
        ('machine_detection_sensitivity_telnyx', sa.Float()),
        ('response_delay_seconds', sa.Float()),
        ('wait_for_greeting', sa.Boolean()),
        ('hyphenation_enabled', sa.Boolean()),
        ('end_call_phrases', sa.JSON()),
        ('response_delay_seconds_phone', sa.Float()),
        ('wait_for_greeting_phone', sa.Boolean()),
        ('hyphenation_enabled_phone', sa.Boolean()),
        ('end_call_phrases_phone', sa.JSON()),
        ('response_delay_seconds_telnyx', sa.Float()),
        ('wait_for_greeting_telnyx', sa.Boolean()),
        ('hyphenation_enabled_telnyx', sa.Boolean()),
        ('end_call_phrases_telnyx', sa.JSON()),
        ('twilio_account_sid', sa.String()),
        ('twilio_auth_token', sa.String()),
        ('twilio_from_number', sa.String()),
        ('telnyx_api_key', sa.String()),
        ('telnyx_connection_id', sa.String()),
        ('caller_id_phone', sa.String()),
        ('sip_trunk_uri_phone', sa.String()),
        ('sip_auth_user_phone', sa.String()),
        ('sip_auth_pass_phone', sa.String()),
        ('fallback_number_phone', sa.String()),
        ('geo_region_phone', sa.String()),
        ('caller_id_telnyx', sa.String()),
        ('sip_trunk_uri_telnyx', sa.String()),
        ('sip_auth_user_telnyx', sa.String()),
        ('sip_auth_pass_telnyx', sa.String()),
        ('fallback_number_telnyx', sa.String()),
        ('geo_region_telnyx', sa.String()),
        ('tools_schema', sa.JSON()),
        ('tools_async', sa.Boolean()),
        ('client_tools_enabled', sa.Boolean()),
        ('tool_server_url', sa.String()),
        ('tool_server_secret', sa.String()),
        ('tool_timeout_ms', sa.Integer()),
        ('tool_retry_count', sa.Integer()),
        ('tool_error_msg', sa.Text()),
        ('tool_server_url_phone', sa.String()),
        ('tool_server_secret_phone', sa.String()),
        ('tool_timeout_ms_phone', sa.Integer()),
        ('tool_retry_count_phone', sa.Integer()),
        ('tool_error_msg_phone', sa.Text()),
        ('tool_server_url_telnyx', sa.String()),
        ('tool_server_secret_telnyx', sa.String()),
        ('tool_timeout_ms_telnyx', sa.Integer()),
        ('tool_retry_count_telnyx', sa.Integer()),
        ('tool_error_msg_telnyx', sa.Text()),
        ('redact_params', sa.JSON()),
        ('transfer_whitelist', sa.JSON()),
        ('state_injection_enabled', sa.Boolean()),
        ('redact_params_phone', sa.JSON()),
        ('transfer_whitelist_phone', sa.JSON()),
        ('state_injection_enabled_phone', sa.Boolean()),
        ('redact_params_telnyx', sa.JSON()),
        ('transfer_whitelist_telnyx', sa.JSON()),
        ('state_injection_enabled_telnyx', sa.Boolean()),
        ('recording_enabled_phone', sa.Boolean()),
        ('recording_channels_phone', sa.String()),
        ('hipaa_enabled_phone', sa.Boolean()),
        ('recording_channels_telnyx', sa.String()),
        ('hipaa_enabled_telnyx', sa.Boolean()),
        ('transfer_type_phone', sa.String()),
        ('dtmf_generation_enabled_phone', sa.Boolean()),
        ('dtmf_listening_enabled_phone', sa.Boolean()),
        ('transfer_type_telnyx', sa.String()),
        ('dtmf_generation_enabled_telnyx', sa.Boolean()),
        ('dtmf_listening_enabled_telnyx', sa.Boolean()),
        ('async_tools', sa.Boolean()),
        ('tools_schema_phone', sa.JSON()),
        ('async_tools_phone', sa.Boolean()),
        ('tools_schema_telnyx', sa.JSON()),
        ('async_tools_telnyx', sa.Boolean()),
        ('analysis_prompt', sa.Text()),
        ('success_rubric', sa.Text()),
        ('extraction_schema', sa.JSON()),
        ('analysis_prompt_phone', sa.Text()),
        ('success_rubric_phone', sa.Text()),
        ('extraction_schema_phone', sa.JSON()),
        ('analysis_prompt_telnyx', sa.Text()),
        ('success_rubric_telnyx', sa.Text()),
        ('extraction_schema_telnyx', sa.JSON()),
        ('sentiment_analysis', sa.Boolean()),
        ('transcript_format', sa.String()),
        ('cost_tracking_enabled', sa.Boolean()),
        ('sentiment_analysis_phone', sa.Boolean()),
        ('transcript_format_phone', sa.String()),
        ('cost_tracking_enabled_phone', sa.Boolean()),
        ('sentiment_analysis_telnyx', sa.Boolean()),
        ('transcript_format_telnyx', sa.String()),
        ('cost_tracking_enabled_telnyx', sa.Boolean()),
        ('log_webhook_url', sa.String()),
        ('pii_redaction_enabled', sa.Boolean()),
        ('retention_days', sa.Integer()),
        ('webhook_url_phone', sa.String()),
        ('webhook_secret_phone', sa.String()),
        ('log_webhook_url_phone', sa.String()),
        ('pii_redaction_enabled_phone', sa.Boolean()),
        ('retention_days_phone', sa.Integer()),
        ('log_webhook_url_telnyx', sa.String()),
        ('pii_redaction_enabled_telnyx', sa.Boolean()),
        ('retention_days_telnyx', sa.Integer()),
        ('custom_headers', sa.JSON()),
        ('sub_account_id', sa.String()),
        ('allowed_api_keys', sa.JSON()),
        ('environment_phone', sa.String()),
        ('privacy_mode_phone', sa.Boolean()),
        ('environment_telnyx', sa.String()),
    ]

    for col_name, col_type in new_columns:
        if col_name not in current_columns:
            op.add_column('agent_configs', sa.Column(col_name, col_type, nullable=True))
    op.alter_column('agent_configs', 'frequency_penalty',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'presence_penalty',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'dynamic_vars_enabled',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('agent_configs', 'idle_message',
               existing_type=sa.VARCHAR(),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('agent_configs', 'frequency_penalty_phone',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'presence_penalty_phone',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'dynamic_vars_enabled_phone',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('agent_configs', 'frequency_penalty_telnyx',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'presence_penalty_telnyx',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'dynamic_vars_enabled_telnyx',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    existing_indexes = {i['name'] for i in inspector.get_indexes('agent_configs')}
    if 'ix_agent_configs_name' in existing_indexes:
        op.drop_index(op.f('ix_agent_configs_name'), table_name='agent_configs')
    
    # Check if unique constraint exists (optional, but good for safety)
    # For now, just try creating the unique constraint/index if needed. 
    # But since create_unique_constraint doesn't have an easy reliable name check in all DBs without explicit naming,
    # we'll rely on the fact we just dropped the non-unique one.
    
    # Note: Alembic's op.create_unique_constraint usually requires a name.
    # The original code had name=None, which implies an auto-generated name.
    # To be safe against "already exists", we can skip if we think it's done, but let's just use ignore_errors logic or simple check.
    
    # Re-creating unique constraint/index might fail if it exists. 
    # Let's inspect unique constraints.
    existing_constraints = {c['name'] for c in inspector.get_unique_constraints('agent_configs')}
    # If the constraint was named explicitly we could check. Since it was None, it's hard. 
    # We will assume if 'ix_agent_configs_name' was absent, maybe we already migrated.
    
    # Re-attempting create_index for transcripts call_id
    existing_transcripts_indexes = {i['name'] for i in inspector.get_indexes('transcripts')}
    if 'ix_transcripts_call_id' not in existing_transcripts_indexes:
        op.create_index(op.f('ix_transcripts_call_id'), 'transcripts', ['call_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_transcripts_call_id'), table_name='transcripts')
    op.drop_constraint(None, 'agent_configs', type_='unique')
    op.create_index(op.f('ix_agent_configs_name'), 'agent_configs', ['name'], unique=True)
    op.alter_column('agent_configs', 'dynamic_vars_enabled_telnyx',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('agent_configs', 'presence_penalty_telnyx',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'frequency_penalty_telnyx',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'dynamic_vars_enabled_phone',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('agent_configs', 'presence_penalty_phone',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'frequency_penalty_phone',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'idle_message',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.alter_column('agent_configs', 'dynamic_vars_enabled',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('agent_configs', 'presence_penalty',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text("'0'::double precision"))
    op.alter_column('agent_configs', 'frequency_penalty',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text("'0'::double precision"))
    op.drop_column('agent_configs', 'environment_telnyx')
    op.drop_column('agent_configs', 'privacy_mode_phone')
    op.drop_column('agent_configs', 'environment_phone')
    op.drop_column('agent_configs', 'allowed_api_keys')
    op.drop_column('agent_configs', 'sub_account_id')
    op.drop_column('agent_configs', 'custom_headers')
    op.drop_column('agent_configs', 'retention_days_telnyx')
    op.drop_column('agent_configs', 'pii_redaction_enabled_telnyx')
    op.drop_column('agent_configs', 'log_webhook_url_telnyx')
    op.drop_column('agent_configs', 'retention_days_phone')
    op.drop_column('agent_configs', 'pii_redaction_enabled_phone')
    op.drop_column('agent_configs', 'log_webhook_url_phone')
    op.drop_column('agent_configs', 'webhook_secret_phone')
    op.drop_column('agent_configs', 'webhook_url_phone')
    op.drop_column('agent_configs', 'retention_days')
    op.drop_column('agent_configs', 'pii_redaction_enabled')
    op.drop_column('agent_configs', 'log_webhook_url')
    op.drop_column('agent_configs', 'cost_tracking_enabled_telnyx')
    op.drop_column('agent_configs', 'transcript_format_telnyx')
    op.drop_column('agent_configs', 'sentiment_analysis_telnyx')
    op.drop_column('agent_configs', 'cost_tracking_enabled_phone')
    op.drop_column('agent_configs', 'transcript_format_phone')
    op.drop_column('agent_configs', 'sentiment_analysis_phone')
    op.drop_column('agent_configs', 'cost_tracking_enabled')
    op.drop_column('agent_configs', 'transcript_format')
    op.drop_column('agent_configs', 'sentiment_analysis')
    op.drop_column('agent_configs', 'extraction_schema_telnyx')
    op.drop_column('agent_configs', 'success_rubric_telnyx')
    op.drop_column('agent_configs', 'analysis_prompt_telnyx')
    op.drop_column('agent_configs', 'extraction_schema_phone')
    op.drop_column('agent_configs', 'success_rubric_phone')
    op.drop_column('agent_configs', 'analysis_prompt_phone')
    op.drop_column('agent_configs', 'extraction_schema')
    op.drop_column('agent_configs', 'success_rubric')
    op.drop_column('agent_configs', 'analysis_prompt')
    op.drop_column('agent_configs', 'async_tools_telnyx')
    op.drop_column('agent_configs', 'tools_schema_telnyx')
    op.drop_column('agent_configs', 'async_tools_phone')
    op.drop_column('agent_configs', 'tools_schema_phone')
    op.drop_column('agent_configs', 'async_tools')
    op.drop_column('agent_configs', 'dtmf_listening_enabled_telnyx')
    op.drop_column('agent_configs', 'dtmf_generation_enabled_telnyx')
    op.drop_column('agent_configs', 'transfer_type_telnyx')
    op.drop_column('agent_configs', 'dtmf_listening_enabled_phone')
    op.drop_column('agent_configs', 'dtmf_generation_enabled_phone')
    op.drop_column('agent_configs', 'transfer_type_phone')
    op.drop_column('agent_configs', 'hipaa_enabled_telnyx')
    op.drop_column('agent_configs', 'recording_channels_telnyx')
    op.drop_column('agent_configs', 'hipaa_enabled_phone')
    op.drop_column('agent_configs', 'recording_channels_phone')
    op.drop_column('agent_configs', 'recording_enabled_phone')
    op.drop_column('agent_configs', 'state_injection_enabled_telnyx')
    op.drop_column('agent_configs', 'transfer_whitelist_telnyx')
    op.drop_column('agent_configs', 'redact_params_telnyx')
    op.drop_column('agent_configs', 'state_injection_enabled_phone')
    op.drop_column('agent_configs', 'transfer_whitelist_phone')
    op.drop_column('agent_configs', 'redact_params_phone')
    op.drop_column('agent_configs', 'state_injection_enabled')
    op.drop_column('agent_configs', 'transfer_whitelist')
    op.drop_column('agent_configs', 'redact_params')
    op.drop_column('agent_configs', 'tool_error_msg_telnyx')
    op.drop_column('agent_configs', 'tool_retry_count_telnyx')
    op.drop_column('agent_configs', 'tool_timeout_ms_telnyx')
    op.drop_column('agent_configs', 'tool_server_secret_telnyx')
    op.drop_column('agent_configs', 'tool_server_url_telnyx')
    op.drop_column('agent_configs', 'tool_error_msg_phone')
    op.drop_column('agent_configs', 'tool_retry_count_phone')
    op.drop_column('agent_configs', 'tool_timeout_ms_phone')
    op.drop_column('agent_configs', 'tool_server_secret_phone')
    op.drop_column('agent_configs', 'tool_server_url_phone')
    op.drop_column('agent_configs', 'tool_error_msg')
    op.drop_column('agent_configs', 'tool_retry_count')
    op.drop_column('agent_configs', 'tool_timeout_ms')
    op.drop_column('agent_configs', 'tool_server_secret')
    op.drop_column('agent_configs', 'tool_server_url')
    op.drop_column('agent_configs', 'client_tools_enabled')
    op.drop_column('agent_configs', 'tools_async')
    op.drop_column('agent_configs', 'tools_schema')
    op.drop_column('agent_configs', 'geo_region_telnyx')
    op.drop_column('agent_configs', 'fallback_number_telnyx')
    op.drop_column('agent_configs', 'sip_auth_pass_telnyx')
    op.drop_column('agent_configs', 'sip_auth_user_telnyx')
    op.drop_column('agent_configs', 'sip_trunk_uri_telnyx')
    op.drop_column('agent_configs', 'caller_id_telnyx')
    op.drop_column('agent_configs', 'geo_region_phone')
    op.drop_column('agent_configs', 'fallback_number_phone')
    op.drop_column('agent_configs', 'sip_auth_pass_phone')
    op.drop_column('agent_configs', 'sip_auth_user_phone')
    op.drop_column('agent_configs', 'sip_trunk_uri_phone')
    op.drop_column('agent_configs', 'caller_id_phone')
    op.drop_column('agent_configs', 'telnyx_connection_id')
    op.drop_column('agent_configs', 'telnyx_api_key')
    op.drop_column('agent_configs', 'twilio_from_number')
    op.drop_column('agent_configs', 'twilio_auth_token')
    op.drop_column('agent_configs', 'twilio_account_sid')
    op.drop_column('agent_configs', 'end_call_phrases_telnyx')
    op.drop_column('agent_configs', 'hyphenation_enabled_telnyx')
    op.drop_column('agent_configs', 'wait_for_greeting_telnyx')
    op.drop_column('agent_configs', 'response_delay_seconds_telnyx')
    op.drop_column('agent_configs', 'end_call_phrases_phone')
    op.drop_column('agent_configs', 'hyphenation_enabled_phone')
    op.drop_column('agent_configs', 'wait_for_greeting_phone')
    op.drop_column('agent_configs', 'response_delay_seconds_phone')
    op.drop_column('agent_configs', 'end_call_phrases')
    op.drop_column('agent_configs', 'hyphenation_enabled')
    op.drop_column('agent_configs', 'wait_for_greeting')
    op.drop_column('agent_configs', 'response_delay_seconds')
    op.drop_column('agent_configs', 'machine_detection_sensitivity_telnyx')
    op.drop_column('agent_configs', 'voicemail_message_telnyx')
    op.drop_column('agent_configs', 'voicemail_detection_enabled_telnyx')
    op.drop_column('agent_configs', 'machine_detection_sensitivity_phone')
    op.drop_column('agent_configs', 'voicemail_message_phone')
    op.drop_column('agent_configs', 'voicemail_detection_enabled_phone')
    op.drop_column('agent_configs', 'machine_detection_sensitivity')
    op.drop_column('agent_configs', 'voicemail_message')
    op.drop_column('agent_configs', 'voicemail_detection_enabled')
    op.drop_column('agent_configs', 'interruption_phrases_telnyx')
    op.drop_column('agent_configs', 'interruption_sensitivity_telnyx')
    op.drop_column('agent_configs', 'barge_in_enabled_telnyx')
    op.drop_column('agent_configs', 'interruption_phrases_phone')
    op.drop_column('agent_configs', 'interruption_sensitivity_phone')
    op.drop_column('agent_configs', 'barge_in_enabled_phone')
    op.drop_column('agent_configs', 'interruption_phrases')
    op.drop_column('agent_configs', 'interruption_sensitivity')
    op.drop_column('agent_configs', 'barge_in_enabled')
    # ### end Alembic commands ###
