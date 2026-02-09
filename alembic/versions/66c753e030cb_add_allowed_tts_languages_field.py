"""add_allowed_tts_languages_field

Revision ID: 66c753e030cb
Revises: c7d7ba081e00
Create Date: 2026-02-09 18:52:07.395852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66c753e030cb'
down_revision: Union[str, Sequence[str], None] = 'c7d7ba081e00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add allowed_tts_languages field to agent_configs table."""
    # Add new column (nullable initially)
    op.add_column('agent_configs', sa.Column('allowed_tts_languages', sa.String(), nullable=True))
    
    # Set default value for existing rows
    op.execute("UPDATE agent_configs SET allowed_tts_languages = 'es-MX,es-US,en-US' WHERE allowed_tts_languages IS NULL")


def downgrade() -> None:
    """Remove allowed_tts_languages field from agent_configs table."""
    op.drop_column('agent_configs', 'allowed_tts_languages')

