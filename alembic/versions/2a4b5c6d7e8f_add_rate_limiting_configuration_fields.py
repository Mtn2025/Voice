"""Add rate limiting configuration fields

Revision ID: 2a4b5c6d7e8f
Revises: c9f05c1b0a49
Create Date: 2026-01-06 21:42:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a4b5c6d7e8f'
down_revision = 'c9f05c1b0a49'
branch_labels = None
depends_on = None


def upgrade():
    # Add rate limiting columns to agent_configs
    op.add_column('agent_configs', sa.Column('rate_limit_global', sa.Integer(), nullable=True, server_default='200'))
    op.add_column('agent_configs', sa.Column('rate_limit_twilio', sa.Integer(), nullable=True, server_default='30'))
    op.add_column('agent_configs', sa.Column('rate_limit_telnyx', sa.Column('rate_limit_websocket', sa.Integer(), nullable=True, server_default='100'))
    
    # Add provider limit columns
    op.add_column('agent_configs', sa.Column('limit_groq_tokens_per_min', sa.Integer(), nullable=True, server_default='100000'))
    op.add_column('agent_configs', sa.Column('limit_azure_requests_per_min', sa.Integer(), nullable=True, server_default='100'))
    op.add_column('agent_configs', sa.Column('limit_twilio_calls_per_hour', sa.Integer(), nullable=True, server_default='100'))
    op.add_column('agent_configs', sa.Column('limit_telnyx_calls_per_hour', sa.Integer(), nullable=True, server_default='100'))


def downgrade():
    # Remove rate limiting columns
    op.drop_column('agent_configs', 'limit_telnyx_calls_per_hour')
    op.drop_column('agent_configs', 'limit_twilio_calls_per_hour')
    op.drop_column('agent_configs', 'limit_azure_requests_per_min')
    op.drop_column('agent_configs', 'limit_groq_tokens_per_min')
    op.drop_column('agent_configs', 'rate_limit_websocket')
    op.drop_column('agent_configs', 'rate_limit_telnyx')
    op.drop_column('agent_configs', 'rate_limit_twilio')
    op.drop_column('agent_configs', 'rate_limit_global')
