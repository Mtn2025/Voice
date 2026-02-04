"""add telnyx integrations

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-01-31 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Webhook/CRM columns for Telnyx Profile
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    if 'webhook_url_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('webhook_url_telnyx', sa.String(), nullable=True))
    if 'webhook_secret_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('webhook_secret_telnyx', sa.String(), nullable=True))
    if 'crm_enabled_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('crm_enabled_telnyx', sa.Boolean(), server_default='false', nullable=True))
    if 'baserow_token_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('baserow_token_telnyx', sa.String(), nullable=True))
    if 'baserow_table_id_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('baserow_table_id_telnyx', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_config', 'baserow_table_id_telnyx')
    op.drop_column('agent_config', 'baserow_token_telnyx')
    op.drop_column('agent_config', 'crm_enabled_telnyx')
    op.drop_column('agent_config', 'webhook_secret_telnyx')
    op.drop_column('agent_config', 'webhook_url_telnyx')
