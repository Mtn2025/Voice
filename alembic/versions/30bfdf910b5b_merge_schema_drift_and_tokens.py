"""merge_schema_drift_and_tokens

Revision ID: 30bfdf910b5b
Revises: 103d76d39916, 4c366cf85347
Create Date: 2026-02-03 22:23:59.262499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30bfdf910b5b'
down_revision: Union[str, Sequence[str], None] = ('103d76d39916', '4c366cf85347')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
