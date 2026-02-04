"""add_system_tab_columns

Revision ID: f4a5b6c7d8e9
Revises: ccda987b1c34
Create Date: 2026-01-31 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'ccda987b1c34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SYSTEM TAB (PHASE VIII)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    if 'concurrency_limit' not in columns:
        op.add_column('agent_configs', sa.Column('concurrency_limit', sa.Integer(), server_default='10', nullable=True))
    if 'spend_limit_daily' not in columns:
        op.add_column('agent_configs', sa.Column('spend_limit_daily', sa.Float(), server_default='50.0', nullable=True))
    if 'environment' not in columns:
        op.add_column('agent_configs', sa.Column('environment', sa.String(), server_default='development', nullable=True))
    if 'privacy_mode' not in columns:
        op.add_column('agent_configs', sa.Column('privacy_mode', sa.Boolean(), server_default='false', nullable=True))
    if 'audit_log_enabled' not in columns:
        op.add_column('agent_configs', sa.Column('audit_log_enabled', sa.Boolean(), server_default='true', nullable=True))


def downgrade() -> None:
    op.drop_column('agent_config', 'audit_log_enabled')
    op.drop_column('agent_config', 'privacy_mode')
    op.drop_column('agent_config', 'environment')
    op.drop_column('agent_config', 'spend_limit_daily')
    op.drop_column('agent_config', 'concurrency_limit')
