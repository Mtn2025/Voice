"""add_llm_advanced_controls_context_penalties_dynamic_vars

Revision ID: llm_controls_v1
Revises: 2a4b5c6d7e8f
Create Date: 2026-01-29 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'llm_controls_v1'
down_revision = '2a4b5c6d7e8f'  # add_rate_limiting_configuration_fields
branch_labels = None
depends_on = None


def upgrade():
    """Add 18 new LLM control fields (6 controls × 3 profiles)."""
    
    # Browser Profile (6 campos)
    op.add_column('agent_configs', sa.Column('context_window', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('agent_configs', sa.Column('frequency_penalty', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('presence_penalty', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('tool_choice', sa.String(), nullable=False, server_default='auto'))
    op.add_column('agent_configs', sa.Column('dynamic_vars_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('dynamic_vars', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Twilio Profile (phone suffix - 6 campos)
    op.add_column('agent_configs', sa.Column('context_window_phone', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('agent_configs', sa.Column('frequency_penalty_phone', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('presence_penalty_phone', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('tool_choice_phone', sa.String(), nullable=False, server_default='auto'))
    op.add_column('agent_configs', sa.Column('dynamic_vars_enabled_phone', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('dynamic_vars_phone', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Telnyx Profile (telnyx suffix - 6 campos)
    op.add_column('agent_configs', sa.Column('context_window_telnyx', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('agent_configs', sa.Column('frequency_penalty_telnyx', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('presence_penalty_telnyx', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('agent_configs', sa.Column('tool_choice_telnyx', sa.String(), nullable=False, server_default='auto'))
    op.add_column('agent_configs', sa.Column('dynamic_vars_enabled_telnyx', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('dynamic_vars_telnyx', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    """Remove 18 LLM control fields."""
    
    # Browser Profile
    op.drop_column('agent_configs', 'dynamic_vars')
    op.drop_column('agent_configs', 'dynamic_vars_enabled')
    op.drop_column('agent_configs', 'tool_choice')
    op.drop_column('agent_configs', 'presence_penalty')
    op.drop_column('agent_configs', 'frequency_penalty')
    op.drop_column('agent_configs', 'context_window')
    
    # Twilio Profile
    op.drop_column('agent_configs', 'dynamic_vars_phone')
    op.drop_column('agent_configs', 'dynamic_vars_enabled_phone')
    op.drop_column('agent_configs', 'tool_choice_phone')
    op.drop_column('agent_configs', 'presence_penalty_phone')
    op.drop_column('agent_configs', 'frequency_penalty_phone')
    op.drop_column('agent_configs', 'context_window_phone')
    
    # Telnyx Profile
    op.drop_column('agent_configs', 'dynamic_vars_telnyx')
    op.drop_column('agent_configs', 'dynamic_vars_enabled_telnyx')
    op.drop_column('agent_configs', 'tool_choice_telnyx')
    op.drop_column('agent_configs', 'presence_penalty_telnyx')
    op.drop_column('agent_configs', 'frequency_penalty_telnyx')
    op.drop_column('agent_configs', 'context_window_telnyx')
