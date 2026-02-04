"""add_model_parameters_temp_tokens

Revision ID: 4c366cf85347
Revises: 7h8i9j0k1l2m
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c366cf85347'
down_revision: Union[str, None] = '7h8i9j0k1l2m'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add temperature and max_tokens
    op.add_column('agent_configs', sa.Column('temperature', sa.Float(), server_default='0.7', nullable=True))
    op.add_column('agent_configs', sa.Column('max_tokens', sa.Integer(), server_default='250', nullable=True))

def downgrade() -> None:
    op.drop_column('agent_configs', 'max_tokens')
    op.drop_column('agent_configs', 'temperature')
