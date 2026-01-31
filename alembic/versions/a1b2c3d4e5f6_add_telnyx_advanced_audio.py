"""add telnyx advanced audio

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-01-31 16:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Advanced Audio columns for Telnyx Profile (Isolation)
    op.add_column('agent_config', sa.Column('audio_codec_telnyx', sa.String(), server_default='PCMU', nullable=True))
    op.add_column('agent_config', sa.Column('noise_suppression_level_telnyx', sa.String(), server_default='balanced', nullable=True))
    op.add_column('agent_config', sa.Column('enable_backchannel_telnyx', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    op.drop_column('agent_config', 'enable_backchannel_telnyx')
    op.drop_column('agent_config', 'noise_suppression_level_telnyx')
    op.drop_column('agent_config', 'audio_codec_telnyx')
