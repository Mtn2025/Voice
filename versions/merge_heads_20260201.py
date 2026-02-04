"""merge multiple heads for audit

Revision ID: merge_heads_20260201
Revises: d84c2c0519f0, ff035ed87960, c1d2e3f4g5h6, a1b2c3d4e5f6
Create Date: 2026-02-01 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_heads_20260201'
down_revision: Union[str, Sequence[str], None] = ('d84c2c0519f0', 'ff035ed87960', 'c1d2e3f4g5h6', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
