"""remove obsolete columns

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5g6
Create Date: 2026-01-31 16:50:00.000000

Removes 7 confirmed obsolete columns from agent_configs table:
- voice_id_manual (deprecated, replaced by voice_name)
- input_min_characters (experimental, unused)
- punctuation_boundaries (feature not implemented)
- segmentation_max_time (STT legacy setting)
- segmentation_strategy (STT legacy setting)
- extra_settings_phone (catch-all JSON, unused)
- telnyx_api_user (use telnyx_api_key instead)

Impact: None - columns confirmed as not used in codebase
Risk: Very low
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'b1c2d3e4f5g6'
branch_labels = None
depends_on = None


def upgrade():
    """Remove 7 confirmed obsolete columns."""
    # Drop columns in order (safest to least safe)
    op.drop_column('agent_configs', 'voice_id_manual')
    op.drop_column('agent_configs', 'input_min_characters')
    op.drop_column('agent_configs', 'punctuation_boundaries')
    op.drop_column('agent_configs', 'segmentation_max_time')
    op.drop_column('agent_configs', 'segmentation_strategy')
    op.drop_column('agent_configs', 'extra_settings_phone')
    op.drop_column('agent_configs', 'telnyx_api_user')


def downgrade():
    """Restore columns if needed (nullable for safety)."""
    op.add_column('agent_configs', sa.Column('voice_id_manual', sa.VARCHAR(), nullable=True))
    op.add_column('agent_configs', sa.Column('input_min_characters', sa.INTEGER(), nullable=True))
    op.add_column('agent_configs', sa.Column('punctuation_boundaries', sa.VARCHAR(), nullable=True))
    op.add_column('agent_configs', sa.Column('segmentation_max_time', sa.INTEGER(), nullable=True))
    op.add_column('agent_configs', sa.Column('segmentation_strategy', sa.VARCHAR(), nullable=True))
    op.add_column('agent_configs', sa.Column('extra_settings_phone', sa.JSON(), nullable=True))
    op.add_column('agent_configs', sa.Column('telnyx_api_user', sa.VARCHAR(), nullable=True))
