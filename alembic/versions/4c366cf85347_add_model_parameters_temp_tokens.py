"""add_model_parameters_temp_tokens

Revision ID: 4c366cf85347
Revises: merge_heads_20260201
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c366cf85347'
down_revision: Union[str, None] = 'merge_heads_20260201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add temperature and max_tokens safely
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('agent_configs')]

    if 'temperature' not in columns:
        op.add_column('agent_configs', sa.Column('temperature', sa.Float(), server_default='0.7', nullable=True))
    if 'max_tokens' not in columns:
        op.add_column('agent_configs', sa.Column('max_tokens', sa.Integer(), server_default='250', nullable=True))

def downgrade() -> None:
    op.drop_column('agent_configs', 'max_tokens')
    op.drop_column('agent_configs', 'temperature')
