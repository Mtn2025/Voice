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
    # Conversation Style Controls
    op.add_column('agent_configs', sa.Column('response_length', sa.String(), nullable=True, server_default='short'))
    op.add_column('agent_configs', sa.Column('conversation_tone', sa.String(), nullable=True, server_default='warm'))
    op.add_column('agent_configs', sa.Column('conversation_formality', sa.String(), nullable=True, server_default='semi_formal'))
    op.add_column('agent_configs', sa.Column('conversation_pacing', sa.String(), nullable=True, server_default='moderate'))

    # CRM Integration
    op.add_column('agent_configs', sa.Column('crm_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('agent_configs', sa.Column('baserow_token', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('baserow_table_id', sa.Integer(), nullable=True))

    # Webhook Integration
    op.add_column('agent_configs', sa.Column('webhook_url', sa.String(), nullable=True))
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
