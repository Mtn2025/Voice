"""merge multiple heads

Revision ID: 7fef3e216110
Revises: 94744f4132ab, a1b2c3d4e5f7, c1d2e3f4g5h6, ff035ed87960
Create Date: 2026-01-31 18:33:58.050445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fef3e216110'
down_revision: Union[str, Sequence[str], None] = ('94744f4132ab', 'a1b2c3d4e5f7', 'c1d2e3f4g5h6', 'ff035ed87960')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
