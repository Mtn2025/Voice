"""add features viii

Revision ID: 008_features_viii
Revises: merge_heads_20260201
Create Date: 2026-02-02 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_features_viii'
down_revision: Union[str, None] = ('7fef3e216110', 'audit_transcription_defaults')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add extracted_data to calls table
    # We use batch_alter_table for SQLite compatibility just in case, though adding a column is usually safe.
    # checks if extracted_data exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('calls')]
    if 'extracted_data' not in columns:
        with op.batch_alter_table('calls', schema=None) as batch_op:
            batch_op.add_column(sa.Column('extracted_data', sa.JSON(), nullable=True))
    
    # 2. Create transcripts table
    if not inspector.has_table('transcripts'):
        op.create_table('transcripts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('call_id', sa.Integer(), nullable=True),
            sa.Column('role', sa.String(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_transcripts_call_id'), 'transcripts', ['call_id'], unique=False)
        op.create_index(op.f('ix_transcripts_id'), 'transcripts', ['id'], unique=False)


def downgrade() -> None:
    # 1. Drop transcripts table
    op.drop_index(op.f('ix_transcripts_id'), table_name='transcripts')
    op.drop_index(op.f('ix_transcripts_call_id'), table_name='transcripts')
    op.drop_table('transcripts')

    # 2. Drop extracted_data from calls
    with op.batch_alter_table('calls', schema=None) as batch_op:
        batch_op.drop_column('extracted_data')
