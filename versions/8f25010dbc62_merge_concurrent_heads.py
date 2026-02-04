"""merge_concurrent_heads

Revision ID: 8f25010dbc62
Revises: tts_controls_v2, e2f3a4b5c6d7
Create Date: 2026-01-29 20:05:48.048685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f25010dbc62'
down_revision: Union[str, Sequence[str], None] = ('tts_controls_v2', 'e2f3a4b5c6d7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
