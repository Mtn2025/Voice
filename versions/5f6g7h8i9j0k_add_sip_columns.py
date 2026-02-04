"""add_sip_and_connectivity_columns

Revision ID: 5f6g7h8i9j0k
Revises: e2f3a4b5c6d7
Create Date: 2026-02-03 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f6g7h8i9j0k'
down_revision = '103d76d39916'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Telnyx SIP & Connectivity
    op.add_column('agent_configs', sa.Column('sip_trunk_uri_telnyx', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('sip_auth_user_telnyx', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('sip_auth_pass_telnyx', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('caller_id_telnyx', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('fallback_number_telnyx', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('geo_region_telnyx', sa.String(), server_default='us-central'))
    
    # Twilio SIP & Connectivity
    op.add_column('agent_configs', sa.Column('sip_trunk_uri_phone', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('sip_auth_user_phone', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('sip_auth_pass_phone', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('caller_id_phone', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('fallback_number_phone', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('geo_region_phone', sa.String(), server_default='us-east-virginia'))


def downgrade() -> None:
    op.drop_column('agent_configs', 'geo_region_phone')
    op.drop_column('agent_configs', 'fallback_number_phone')
    op.drop_column('agent_configs', 'caller_id_phone')
    op.drop_column('agent_configs', 'sip_auth_pass_phone')
    op.drop_column('agent_configs', 'sip_auth_user_phone')
    op.drop_column('agent_configs', 'sip_trunk_uri_phone')
    
    op.drop_column('agent_configs', 'geo_region_telnyx')
    op.drop_column('agent_configs', 'fallback_number_telnyx')
    op.drop_column('agent_configs', 'caller_id_telnyx')
    op.drop_column('agent_configs', 'sip_auth_pass_telnyx')
    op.drop_column('agent_configs', 'sip_auth_user_telnyx')
    op.drop_column('agent_configs', 'sip_trunk_uri_telnyx')
