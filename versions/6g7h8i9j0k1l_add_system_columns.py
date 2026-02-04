"""add_system_columns

Revision ID: 6g7h8i9j0k1l
Revises: 5f6g7h8i9j0k
Create Date: 2026-02-03 19:42:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6g7h8i9j0k1l'
down_revision = '5f6g7h8i9j0k'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # System & Governance (Phase VIII)
    op.add_column('agent_configs', sa.Column('concurrency_limit', sa.Integer(), server_default='10', nullable=True))
    op.add_column('agent_configs', sa.Column('spend_limit_daily', sa.Float(), server_default='50.0', nullable=True))
    op.add_column('agent_configs', sa.Column('environment', sa.String(), server_default='development', nullable=True))
    op.add_column('agent_configs', sa.Column('privacy_mode', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('agent_configs', sa.Column('audit_log_enabled', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    op.drop_column('agent_configs', 'audit_log_enabled')
    op.drop_column('agent_configs', 'privacy_mode')
    op.drop_column('agent_configs', 'environment')
    op.drop_column('agent_configs', 'spend_limit_daily')
    op.drop_column('agent_configs', 'concurrency_limit')
