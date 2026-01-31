"""add telnyx system safety

Revision ID: a1b2c3d4e5f7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-31 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add System & Safety columns for Telnyx Profile (Isolation)
    op.add_column('agent_config', sa.Column('max_retries_telnyx', sa.Integer(), server_default='3', nullable=True))
    op.add_column('agent_config', sa.Column('concurrency_limit_telnyx', sa.Integer(), nullable=True))
    op.add_column('agent_config', sa.Column('daily_spend_limit_telnyx', sa.Float(), nullable=True))
    op.add_column('agent_config', sa.Column('environment_tag_telnyx', sa.String(), server_default='development', nullable=True))
    op.add_column('agent_config', sa.Column('privacy_mode_telnyx', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('agent_config', sa.Column('audit_log_enabled_telnyx', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    op.drop_column('agent_config', 'audit_log_enabled_telnyx')
    op.drop_column('agent_config', 'privacy_mode_telnyx')
    op.drop_column('agent_config', 'environment_tag_telnyx')
    op.drop_column('agent_config', 'daily_spend_limit_telnyx')
    op.drop_column('agent_config', 'concurrency_limit_telnyx')
    op.drop_column('agent_config', 'max_retries_telnyx')
