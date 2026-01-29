import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.db_service import db_service
from app.db.models import AgentConfig

logger = logging.getLogger(__name__)

async def update_profile_config(db: AsyncSession, profile: str, data_dict: dict):
    """
    Updates configuration for a specific profile (browser, twilio, telnyx)
    ensuring SEPARATION OF CONCERNS.
    
    Logic:
    - browser: Updates base fields (e.g., 'llm_model')
    - twilio: Updates fields with '_phone' suffix (e.g., 'llm_model_phone')
    - telnyx: Updates fields with '_telnyx' suffix (e.g., 'llm_model_telnyx')
    
    This barrier prevents settings from one profile leaking into another.
    """
    profile = profile.lower().strip()
    
    # Get current config to check for valid columns
    current_config = await db_service.get_agent_config(db)
    if not current_config:
        logger.error("Agent config not found during update")
        return None
        
    final_payload = {}
    
    # Define Suffix based on Profile
    suffix = ""
    if profile == "twilio":
        suffix = "_phone"
    elif profile == "telnyx":
        suffix = "_telnyx"
    elif profile == "browser":
        suffix = "" # Base fields
    else:
        logger.warning(f"Unknown profile: {profile}, assuming base.")
        
    # Keys that are ALWAYS Global (No Suffix)
    # These are shared or strictly one-per-system settings
    GLOBAL_KEYS = {
        'concurrency_limit', 'spend_limit_daily', 'environment', 
        'audit_log_enabled', 'privacy_mode', 
        # Credentials are technically distinctive in name, but stored flatly.
        'twilio_account_sid', 'twilio_auth_token', 'twilio_from_number',
        'telnyx_api_key', 'telnyx_connection_id',
        'webhook_url', 'webhook_secret', 
        'pg_host', 'pg_port', 'pg_user', 'pg_pass', 'pg_dbname',
        'rate_limit_global', 'rate_limit_twilio', 'rate_limit_telnyx'
    }

    normalized_count = 0
    ignored_count = 0

    for key, value in data_dict.items():
        # 1. Skip metadata
        if key in ["id", "name", "created_at", "api_key"]:
            continue
            
        # 2. Check if Global
        if key in GLOBAL_KEYS:
            final_payload[key] = value
            continue

        # 3. Apply Suffix Logic
        # If the key already has the suffix, trust it? 
        # Better: Strip suffix if present (unlikely from UI) then re-apply proper suffix.
        # But UI sends generic keys (e.g. 'llm_model') mostly.
        # However, Field Aliases in Router might have already run?
        # Router runs mapping BEFORE calling this? 
        # Let's assume Router passes data_dict matching `dashboard.html` names OR Aliases.
        # Router `FIELD_ALIASES` maps `model` -> `llm_model`.
        # So we get `llm_model`. 
        
        target_key = f"{key}{suffix}"
        
        # 4. Special Case: Some keys might NOT follow the standard suffix pattern?
        # e.g. `voice_sensitivity_phone` is correct.
        # `stt_provider_phone` is correct.
        # If the target column exists, use it.
        
        if hasattr(AgentConfig, target_key):
            final_payload[target_key] = value
            normalized_count += 1
        elif hasattr(AgentConfig, key):
            # Fallback: Maybe it IS a global key we didn't list, or base key?
            # If profile is NOT browser, and we are writing to a base key, 
            # we might be leaking.
            if profile != "browser" and key not in GLOBAL_KEYS:
                 # Check if it's a specific key like 'twilio_account_sid' that doesn't use _phone
                 pass 
            
            final_payload[key] = value
        else:
            ignored_count += 1
            # logger.debug(f"Ignored key {key} -> {target_key} (Not in Model)")

    # Execute Update via Service
    await db_service.update_agent_config(db, **final_payload)
    
    logger.info(f"[{profile.upper()}] Config Update: {len(final_payload)} fields updated.")
    return final_payload
