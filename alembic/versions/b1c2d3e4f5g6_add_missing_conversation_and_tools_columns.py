"""add missing conversation and tools columns

Revision ID: b1c2d3e4f5g6
Revises: f4a5b6c7d8e9
Create Date: 2026-01-31 16:26:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing conversation style and tools columns for Phone and Telnyx profiles."""
    
    # Phone Profile - Conversation Style Fields (4 columns)
    op.add_column('agent_configs', sa.Column('response_length_phone', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_tone_phone', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_formality_phone', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_pacing_phone', sa.String(50), nullable=True))
    
    # Telnyx Profile - Conversation Style Fields (4 columns)
    op.add_column('agent_configs', sa.Column('response_length_telnyx', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_tone_telnyx', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_formality_telnyx', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_pacing_telnyx', sa.String(50), nullable=True))
    
    # Telnyx Profile - Tools Configuration (1 column)
    op.add_column('agent_configs', sa.Column('client_tools_enabled_telnyx', sa.Boolean(), nullable=True, server_default='false'))


def downgrade():
    """Remove conversation style and tools columns."""
    
    # Phone Profile
    op.drop_column('agent_configs', 'response_length_phone')
    op.drop_column('agent_configs', 'conversation_tone_phone')
    op.drop_column('agent_configs', 'conversation_formality_phone')
    op.drop_column('agent_configs', 'conversation_pacing_phone')
    
    # Telnyx Profile
    op.drop_column('agent_configs', 'response_length_telnyx')
    op.drop_column('agent_configs', 'conversation_tone_telnyx')
    op.drop_column('agent_configs', 'conversation_formality_telnyx')
    op.drop_column('agent_configs', 'conversation_pacing_telnyx')
    op.drop_column('agent_configs', 'client_tools_enabled_telnyx')
