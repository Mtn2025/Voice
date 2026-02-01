"""add missing crm webhook and style columns

Revision ID: d1e2f3a4b5c6
Revises: ccda987b1c34
Create Date: 2026-01-26 13:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'ccda987b1c34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing CRM, Webhook, and Conversation Style columns."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    # Conversation Style Controls
    if 'response_length' not in columns:
        op.add_column('agent_configs', sa.Column('response_length', sa.String(), nullable=True, server_default='short'))
    if 'conversation_tone' not in columns:
        op.add_column('agent_configs', sa.Column('conversation_tone', sa.String(), nullable=True, server_default='warm'))
    if 'conversation_formality' not in columns:
        op.add_column('agent_configs', sa.Column('conversation_formality', sa.String(), nullable=True, server_default='semi_formal'))
    if 'conversation_pacing' not in columns:
        op.add_column('agent_configs', sa.Column('conversation_pacing', sa.String(), nullable=True, server_default='moderate'))

    # CRM Integration
    if 'crm_enabled' not in columns:
        op.add_column('agent_configs', sa.Column('crm_enabled', sa.Boolean(), nullable=True, server_default='false'))
    if 'baserow_token' not in columns:
        op.add_column('agent_configs', sa.Column('baserow_token', sa.String(), nullable=True))
    if 'baserow_table_id' not in columns:
        op.add_column('agent_configs', sa.Column('baserow_table_id', sa.Integer(), nullable=True))

    # Webhook Integration
    if 'webhook_url' not in columns:
        op.add_column('agent_configs', sa.Column('webhook_url', sa.String(), nullable=True))
    if 'webhook_secret' not in columns:
        op.add_column('agent_configs', sa.Column('webhook_secret', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove added columns."""
    op.drop_column('agent_configs', 'webhook_secret')
    op.drop_column('agent_configs', 'webhook_url')
    op.drop_column('agent_configs', 'baserow_table_id')
    op.drop_column('agent_configs', 'baserow_token')
    op.drop_column('agent_configs', 'crm_enabled')
    op.drop_column('agent_configs', 'conversation_pacing')
    op.drop_column('agent_configs', 'conversation_formality')
    op.drop_column('agent_configs', 'conversation_tone')
    op.drop_column('agent_configs', 'response_length')
