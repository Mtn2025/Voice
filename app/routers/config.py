"""
Configuration management endpoints.
Modular endpoints for browser, twilio, telnyx, and core configurations.
Extracted from dashboard.py as part of post-audit refactoring (Phase 2).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_simple import verify_api_key
from app.db.database import get_db
from app.services.db_service import db_service
from app.schemas.config_schemas import (
    BrowserConfigUpdate,
    CoreConfigUpdate,
    TelnyxConfigUpdate,
    TwilioConfigUpdate,
)

router = APIRouter(prefix="/api/config", tags=["config"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def _persist_to_env(update_data: dict):
    """Persist configuration updates to .env file."""
    try:
        from app.core.config_utils import update_env_file
        updates = {k.upper(): v for k, v in update_data.items()}
        update_env_file(updates)
    except Exception as e:
        logging.warning(f"Could not update .env file: {e}")


# =============================================================================
# Profile-Specific Config Endpoints
# =============================================================================

@router.patch("/browser", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_browser_config(
    request: Request,
    config: BrowserConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update Browser/Simulator profile configuration."""
    try:
        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)
        _persist_to_env(update_data)
        
        return {
            "status": "success",
            "profile": "browser",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }
    except Exception as e:
        logger.error(f"Error updating Browser config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/twilio", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_twilio_config(
    request: Request,
    config: TwilioConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update Twilio/Phone profile configuration."""
    try:
        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)
        _persist_to_env(update_data)
        
        return {
            "status": "success",
            "profile": "twilio",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }
    except Exception as e:
        logger.error(f"Error updating Twilio config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/telnyx", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_telnyx_config(
    request: Request,
    config: TelnyxConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update Telnyx profile configuration."""
    try:
        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)
        _persist_to_env(update_data)
        
        return {
            "status": "success",
            "profile": "telnyx",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }
    except Exception as e:
        logger.error(f"Error updating Telnyx config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/core", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_core_config(
    request: Request,
    config: CoreConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update Core/Global configuration."""
    try:
        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)
        _persist_to_env(update_data)
        
        return {
            "status": "success",
            "profile": "core",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }
    except Exception as e:
        logger.error(f"Error updating Core config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# JSON-based Config Update (AJAX)
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
}


@router.post("/update-json", dependencies=[Depends(verify_api_key)])
async def update_config_json(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    AJAX/JSON config update endpoint with field normalization.
    Maps UI camelCase to DB snake_case.
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
                logger.debug(f"🔀 [NORMALIZE] {key} → {normalized_key}")
            
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
                        value = float(value) if '.' in value else int(value)
                
                setattr(current_config, normalized_key, value)
                updated_count += 1
            else:
                logger.warning(f"⚠️ [CONFIG-JSON] Ignored unknown key: {key}")

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


@router.post("/patch", dependencies=[Depends(verify_api_key)])
async def patch_config(request: Request, db: AsyncSession = Depends(get_db)):
    """
    PATCH endpoint for specific field updates.
    Example: {"input_min_characters": 30}
    """
    try:
        data = await request.json()

        # Type conversion helpers
        int_fields = [
            "input_min_characters", "max_tokens", "silence_timeout_ms",
            "initial_silence_timeout_ms", "segmentation_max_time",
            "interruption_threshold", "max_duration", "inactivity_max_retries"
        ]
        float_fields = [
            "temperature", "voice_speed", "idle_timeout"
        ]
        bool_fields = [
            "enable_denoising", "enable_end_call", "enable_dial_keypad"
        ]

        cleaned_data = {}
        for k, v in data.items():
            if v is None:
                cleaned_data[k] = None
            elif k in int_fields:
                cleaned_data[k] = int(v)
            elif k in float_fields:
                cleaned_data[k] = float(v)
            elif k in bool_fields:
                cleaned_data[k] = v if isinstance(v, bool) else str(v).lower() == 'true'
            else:
                cleaned_data[k] = v

        await db_service.update_agent_config(db, **cleaned_data)
        return {"status": "success", "updated": cleaned_data}
        
    except Exception as e:
        logger.error(f"Config Patch Failed: {e}")
        return {"status": "error", "message": str(e)}
