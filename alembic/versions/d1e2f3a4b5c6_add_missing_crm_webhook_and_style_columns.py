"""add missing crm webhook and style columns

Revision ID: d1e2f3a4b5c6
Revises: ccda987b1c34
Create Date: 2026-01-26 13:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'ccda987b1c34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing CRM, Webhook, and Conversation Style columns safely."""
    # Conversation Style Controls
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS response_length VARCHAR DEFAULT 'short'")
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS conversation_tone VARCHAR DEFAULT 'warm'")
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS conversation_formality VARCHAR DEFAULT 'semi_formal'")
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS conversation_pacing VARCHAR DEFAULT 'moderate'")

    # CRM Integration
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS crm_enabled BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS baserow_token VARCHAR")
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS baserow_table_id INTEGER")

    # Webhook Integration
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS webhook_url VARCHAR")
    op.execute("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS webhook_secret VARCHAR")


def downgrade() -> None:
    """Remove added columns."""
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS webhook_secret")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS webhook_url")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS baserow_table_id")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS baserow_token")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS crm_enabled")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS conversation_pacing")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS conversation_formality")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS conversation_tone")
    op.execute("ALTER TABLE agent_configs DROP COLUMN IF EXISTS response_length")
