"""
Configuration Router - Modular Config Management

Extracted from dashboard.py for clean architecture.
Handles all agent configuration endpoints (browser, twilio, telnyx, core).
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_simple import verify_api_key
from app.db.database import get_db
from app.schemas.config_schemas import (
    BrowserConfigUpdate,
    CoreConfigUpdate,
    TelnyxConfigUpdate,
    TwilioConfigUpdate,
)
from app.services.db_service import db_service
from app.utils.config_utils import update_profile_config

logger = logging.getLogger(__name__)

# =============================================================================
# FIELD MAPPING (Frontend -> Backend)
# =============================================================================
FIELD_ALIASES = {
    # LLM Configuration
    'provider': 'llm_provider',
    'model': 'llm_model',
    'temp': 'temperature',
    'tokens': 'max_tokens',
    'prompt': 'system_prompt',
    'msg': 'first_message',
    'mode': 'first_message_mode',
    
    # TTS Configuration
    'voiceProvider': 'tts_provider',
    'voiceId': 'voice_name',
    'voiceStyle': 'voice_style',
    'voiceSpeed': 'voice_speed',
    'voicePacing': 'voice_pacing_ms',
    'voiceBgSound': 'background_sound',
    'voiceBgUrl': 'background_sound_url',
    'voiceLang': 'voice_language',
    
    # Conversation Style
    'responseLength': 'response_length',
    'conversationTone': 'conversation_tone',
    'conversationFormality': 'conversation_formality',
    'conversationPacing': 'conversation_pacing',
    
    # STT Configuration
    'sttProvider': 'stt_provider',
    'sttLang': 'stt_language',
    'interruptWords': 'interruption_threshold',
    'interruptRMS': 'voice_sensitivity',
    'silence': 'silence_timeout_ms',
    'blacklist': 'hallucination_blacklist',
    'inputMin': 'input_min_characters',
    'vadThreshold': 'vad_threshold',
    
    # Advanced Features
    'denoise': 'enable_denoising',
    'krisp': 'enable_krisp_telnyx',
    'vad': 'enable_vad_telnyx',
    'maxDuration': 'max_duration',
    'maxRetries': 'inactivity_max_retries',
    'idleTimeout': 'idle_timeout',
    'idleMessage': 'idle_message',
    'enableRecording': 'enable_recording_telnyx',
    'amdConfig': 'amd_config_telnyx',
    'enableEndCall': 'enable_end_call',
    'dialKeypad': 'enable_dial_keypad',
    'transferNum': 'transfer_phone_number',
    
    # Quality & Latency
    'noiseSuppressionLevel': 'noise_suppression_level',
    'audioCodec': 'audio_codec',
    'enableBackchannel': 'enable_backchannel',
    'silenceTimeoutMs': 'silence_timeout_ms',
    'silenceTimeoutMsPhone': 'silence_timeout_ms_phone',
    
    # New Advanced LLM Controls
    'contextWindow': 'context_window',
    'frequencyPenalty': 'frequency_penalty',
    'presencePenalty': 'presence_penalty',
    'toolChoice': 'tool_choice',
    'dynamicVarsEnabled': 'dynamic_vars_enabled',
    'dynamicVars': 'dynamic_vars',

    # Connectivity (Credentials & SIP)
    'twilioAccountSid': 'twilio_account_sid',
    'twilioAuthToken': 'twilio_auth_token',
    'twilioFromNumber': 'twilio_from_number',
    'telnyxApiKey': 'telnyx_api_key',
    'telnyxConnectionId': 'telnyx_connection_id',
    'callerIdTelnyx': 'caller_id_telnyx',
    
    # SIP Trunking
    'sipTrunkUriPhone': 'sip_trunk_uri_phone',
    'sipAuthUserPhone': 'sip_auth_user_phone',
    'sipAuthPassPhone': 'sip_auth_pass_phone',
    'fallbackNumberPhone': 'fallback_number_phone',
    'geoRegionPhone': 'geo_region_phone',
    
    'sipTrunkUriTelnyx': 'sip_trunk_uri_telnyx',
    'sipAuthUserTelnyx': 'sip_auth_user_telnyx',
    'sipAuthPassTelnyx': 'sip_auth_pass_telnyx',
    'fallbackNumberTelnyx': 'fallback_number_telnyx',
    'geoRegionTelnyx': 'geo_region_telnyx',
    
    # Features & Compliance
    'recordingChannelsPhone': 'recording_channels_phone',
    'recordingChannelsTelnyx': 'recording_channels_telnyx',
    'hipaaEnabledPhone': 'hipaa_enabled_phone',
    'hipaaEnabledTelnyx': 'hipaa_enabled_telnyx',
    'dtmfListeningEnabledPhone': 'dtmf_listening_enabled_phone',
    
    # System & Governance
    'concurrencyLimit': 'concurrency_limit',
    'spendLimitDaily': 'spend_limit_daily',
    'environment': 'environment',
    'privacyMode': 'privacy_mode',
    'auditLogEnabled': 'audit_log_enabled',
}

router = APIRouter(
    prefix="/api/config",
    tags=["configuration"],
    dependencies=[Depends(verify_api_key)]
)


@router.patch("/browser")
async def update_browser_config(
    request: Request,
    config: BrowserConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Browser/Simulator profile configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Browser profile configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="browser",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update browser config")
        
        logger.info("✅ Browser config updated successfully")
        return {"status": "ok", "message": "Browser config updated"}
    
    except Exception as e:
        logger.error(f"❌ Browser config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/twilio")
async def update_twilio_config(
    request: Request,
    config: TwilioConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Twilio/Phone profile configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Twilio profile configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="twilio",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update Twilio config")
        
        logger.info("✅ Twilio config updated successfully")
        return {"status": "ok", "message": "Twilio config updated"}
    
    except Exception as e:
        logger.error(f"❌ Twilio config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/telnyx")
async def update_telnyx_config(
    request: Request,
    config: TelnyxConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Telnyx profile configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Telnyx profile configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="telnyx",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update Telnyx config")
        
        logger.info("✅ Telnyx config updated successfully")
        return {"status": "ok", "message": "Telnyx config updated"}
    
    except Exception as e:
        logger.error(f"❌ Telnyx config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/core")
async def update_core_config(
    request: Request,
    config: CoreConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Core/Global configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Core configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="core",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update core config")
        
        logger.info("✅ Core config updated successfully")
        return {"status": "ok", "message": "Core config updated"}
    
    except Exception as e:
        logger.error(f"❌ Core config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patch")
async def patch_config(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Accepts JSON payload to update specific config fields.
    Example: {"input_min_characters": 30}
    """
    try:
        body = await request.json()
        logger.info(f"[PATCH] Received config patch: {list(body.keys())}")
        
        # Get current config
        config = await db_service.get_agent_config(db)
        
        if not config:
            raise HTTPException(status_code=404, detail="Agent config not found")
        
        # Update config
        config_dict = config.to_dict() if hasattr(config, 'to_dict') else config.__dict__
        config_dict.update(body)
        
        # Save changes
        await db_service.update_agent_config(db, config_dict)
        
        logger.info("✅ Config patched successfully")
        return {"status": "ok", "updated_fields": list(body.keys())}
    
    except Exception as e:
        logger.error(f"❌ Config patch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-json")
async def update_config_json(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    AJAX/JSON config update endpoint with field normalization.
    Maps UI camelCase to DB snake_case.
    Fixed via Migration from legacy config.py
    """
    try:
        data = await request.json()
        logger.info(f"🔄 [CONFIG-JSON] Received update payload: {len(data)} keys")
        
        current_config = await db_service.get_agent_config(db)
        updated_count = 0
        normalized_count = 0
        
        for key, value in data.items():
            # Skip metadata
            if key in ["id", "name", "created_at", "api_key"]:
                continue
            
            # Normalize field names
            normalized_key = FIELD_ALIASES.get(key, key)
            if normalized_key != key:
                normalized_count += 1
                # logger.debug(f"🔀 [NORMALIZE] {key} → {normalized_key}")
            
            # Check if key exists in model
            if hasattr(current_config, normalized_key):
                # Type conversion
                if value == "":
                    value = None
                elif isinstance(value, str):
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                
                setattr(current_config, normalized_key, value)
                updated_count += 1
            else:
                pass # logger.warning(f"⚠️ [CONFIG-JSON] Ignored unknown key: {key}")

        await db.commit()
        await db.refresh(current_config)
        logger.info(f"✅ [CONFIG-JSON] Updated {updated_count} fields ({normalized_count} normalized).")
        
        return {
            "status": "success",
            "updated": updated_count,
            "normalized": normalized_count
        }
        
    except Exception as e:
        logger.error(f"❌ [CONFIG-JSON] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
