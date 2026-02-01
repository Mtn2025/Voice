"""add vad_threshold columns

Revision ID: ccda987b1c34
Revises: bbbe703ac987
Create Date: 2026-01-26 13:16:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccda987b1c34'
down_revision: Union[str, Sequence[str], None] = 'bbbe703ac987'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add vad_threshold columns to agent_configs."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    if 'vad_threshold' not in columns:
        op.add_column('agent_configs', sa.Column('vad_threshold', sa.Float(), nullable=True, server_default='0.5'))
    if 'vad_threshold_phone' not in columns:
        op.add_column('agent_configs', sa.Column('vad_threshold_phone', sa.Float(), nullable=True, server_default='0.5'))
    if 'vad_threshold_telnyx' not in columns:
        op.add_column('agent_configs', sa.Column('vad_threshold_telnyx', sa.Float(), nullable=True, server_default='0.5'))


def downgrade() -> None:
    """Remove vad_threshold columns."""
    op.drop_column('agent_configs', 'vad_threshold_telnyx')
    op.drop_column('agent_configs', 'vad_threshold_phone')
    op.drop_column('agent_configs', 'vad_threshold')
