"""add quality and latency fields

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-01-28 00:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agent_configs', sa.Column('noise_suppression_level', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('audio_codec', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('enable_backchannel', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_configs', 'enable_backchannel')
    op.drop_column('agent_configs', 'audio_codec')
    op.drop_column('agent_configs', 'noise_suppression_level')
