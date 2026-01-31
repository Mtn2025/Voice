"""add_tools_columns

Revision ID: 94744f4132ab
Revises: 8f25010dbc62
Create Date: 2026-01-31 13:07:53.251695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94744f4132ab'
down_revision: Union[str, Sequence[str], None] = '8f25010dbc62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
