import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.db_service import db_service

logger = logging.getLogger(__name__)

async def update_profile_config(db: AsyncSession, profile: str, data_dict: dict):
    """
    Updates configuration for a specific profile (browser, twilio, telnyx).
    Uses AgentConfig.update_profile() for centralized, type-safe updates.
    """
    from app.schemas.profile_config import ProfileConfigSchema

    profile = profile.lower().strip()

    # Get current config
    current_config = await db_service.get_agent_config(db)
    if not current_config:
        logger.error("Agent config not found during update")
        return None

    # Separate global keys from profile-specific keys
    global_keys = {
        'concurrency_limit', 'spend_limit_daily', 'environment',
        'audit_log_enabled', 'privacy_mode',
        'twilio_account_sid', 'twilio_auth_token', 'twilio_from_number',
        'telnyx_api_key', 'telnyx_connection_id',
        'webhook_url', 'webhook_secret',
        'pg_host', 'pg_port', 'pg_user', 'pg_pass', 'pg_dbname',
        'rate_limit_global', 'rate_limit_twilio', 'rate_limit_telnyx'
    }

    # Split data into global and profile updates
    global_updates = {}
    profile_updates = {}

    for key, value in data_dict.items():
        # Skip metadata
        if key in ["id", "name", "created_at", "api_key"]:
            continue

        # Separate global from profile-specific
        if key in global_keys:
            global_updates[key] = value
        else:
            profile_updates[key] = value

    # Apply global updates directly
    if global_updates:
        for key, value in global_updates.items():
            if hasattr(current_config, key):
                setattr(current_config, key, value)

    # Apply profile updates using ProfileConfigSchema
    if profile_updates:
        try:
            # Create ProfileConfigSchema from updates (validates types)
            profile_schema = ProfileConfigSchema(**profile_updates)

            # Use AgentConfig.update_profile() method
            current_config.update_profile(profile, profile_schema)

            logger.info(f"[{profile.upper()}] Config Update: {len(profile_updates)} profile fields + {len(global_updates)} global fields updated.")
        except Exception as e:
            logger.error(f"Failed to update profile config: {e}")
            return None

    # Commit changes
    await db.commit()
    await db.refresh(current_config)

    return current_config
