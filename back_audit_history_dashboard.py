import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession  # NEW
from pydantic import BaseModel
from typing import Optional, Any

from app.core.auth_simple import verify_api_key, verify_dashboard_access
from app.core.config import settings
from app.core.input_sanitization import (
    register_template_filters,
)
from app.db.database import get_db  # NEW
from app.services.db_service import db_service

# ... (Imports remain)
import secrets

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

# Rate limiter for dashboard endpoints (Security - H-3)
limiter = Limiter(key_func=get_remote_address)

# Register sanitization filters for XSS protection (Punto A5)
template_filters = register_template_filters(None)
templates.env.filters.update(template_filters)

# --- LOGIN ROUTES ---
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("authenticated"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, api_key: str = Form(...)):
    valid_key = getattr(settings, 'ADMIN_API_KEY', None)
    
    if valid_key and secrets.compare_digest(api_key, valid_key):
        request.session["authenticated"] = True
        logger.info(f"✅ User logged in via Dashboard Login from {request.client.host}")
        return RedirectResponse("/dashboard", status_code=302)
    
    logger.warning(f"❌ Failed login attempt from {request.client.host}")
    return templates.TemplateResponse("login.html", {"request": request, "error": "Clave Incorrecta"})

@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(verify_dashboard_access)])
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db) # Injected Session
):
    config = await db_service.get_agent_config(db) # Pass session explicitly

    # Fetch Dynamic Options
    # Use temporary instances or factory if possible.
    # We can instantiate providers directly to get static lists if methods are static/or lightweight
    from app.providers.azure import AzureProvider
    from app.providers.groq import GroqProvider

    # Voices
    tts_provider = AzureProvider() # Lightweight init
    # voice_styles = tts_provider.get_voice_styles() 
    # MOVED Styles below voices to keep logic grouped
    
    # Languages - Mapped by Provider
    # AzureProvider now returns List[Dict] directly
    azure_langs = tts_provider.get_available_languages()

    languages = {
        "azure": azure_langs
    }

    voice_styles = tts_provider.get_voice_styles()

    # Models - CURATED lists with descriptive labels
    # Only voice-appropriate models are included
    models = {
        "groq": [
            {"id": "llama-3.3-70b-versatile", "name": "⭐ Llama 3.3 70B Versatile (MEJOR)"},
            {"id": "llama-3.3-70b-specdec", "name": "Llama 3.3 70B SpecDec (Ultra Rápido)"},
            {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B Versatile"},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8b Instant (Económico)"},
            {"id": "gemma-2-9b-it", "name": "Gemma 2 9B IT"},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
        ],
        "azure": [
            {"id": "gpt-4o", "name": "⭐ GPT-4o (Omni - MEJOR)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Rápido + Económico)"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo (Alta capacidad)"},
            {"id": "gpt-35-turbo", "name": "GPT-3.5 Turbo (Económico)"}
        ]
    }

    voices = {
        "azure": {}
    }

    # Voices - AzureProvider.get_available_voices() usually returns {lang: [Voice...]}
    # We must ensure they are serializable dicts
    azure_voices_raw = tts_provider.get_available_voices()
    
    # Updated Logic for List[Dict] from Provider (Source: AzureProvider.get_available_voices)
    if isinstance(azure_voices_raw, list):
        for v in azure_voices_raw:
            # Check for required dict keys
            if not isinstance(v, dict): continue
            
            locale = v.get("locale")
            if not locale: continue

            # Initialize locale list if missing
            if locale not in voices["azure"]:
                voices["azure"][locale] = []

            # Add normalized voice object
            voices["azure"][locale].append({
                "id": v.get("id"),
                "name": v.get("name"),
                "gender": v.get("gender", "female").lower()
            })
            
    # Legacy Dict Support (Backward Auto-Compat)
    elif isinstance(azure_voices_raw, dict):
        for lang, v_list in azure_voices_raw.items():
            voices["azure"][lang] = []
            for v in v_list:
                v_dict = {}
                # Handle Object with attributes
                if hasattr(v, "id"):
                     v_dict = {
                        "id": v.id, 
                        "name": getattr(v, "local_name", getattr(v, "name", v.id)),
                        "gender": str(getattr(v, "gender", "female")).lower()
                     }
                # Handle Dict
                elif isinstance(v, dict):
                    v_dict = v
                
                if v_dict:
                    voices["azure"][lang].append(v_dict)

    # 2. Static Fallback (CRITICAL for valid UI if API fails)
    if not voices["azure"]:
        voices["azure"] = {
            "es-MX": [
                {"id": "es-MX-DaliaNeural", "name": "Dalia (Neural)", "gender": "female"},
                {"id": "es-MX-JorgeNeural", "name": "Jorge (Neural)", "gender": "male"}
            ],
            "en-US": [
                {"id": "en-US-JennyNeural", "name": "Jenny (Neural)", "gender": "female"}
            ]
        }
    
    # Styles - AzureProvider.get_voice_styles() -> {voice_id: [styles]}
    # Frontend: this.styles[vid] -> list. This seems valid as is (keyed by Voice ID).
    # No change needed for styles if it's keyed by Voice ID.


    history = await db_service.get_recent_calls(session=db, limit=10) # New

    # Helpers for serialization
    def model_to_dict(obj):
        if not obj:
            return {}
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    config_dict = model_to_dict(config)

    # Serialize history manually as well
    history_list = [model_to_dict(call) for call in history]

    import json
    
    # Serialize data for frontend injection
    response = templates.TemplateResponse("dashboard.html", {
        "request": request,
        "config_json": json.dumps(config_dict),
        "voices_json": json.dumps(voices),
        "styles_json": json.dumps(voice_styles),
        "langs_json": json.dumps(languages),
        "models_json": json.dumps(models),
        "history": history_list,
        "protocol": request.url.scheme,
        "host": request.url.netloc
    })
    
    # CRITICAL: Prevent caching of the dashboard to ensure server-config is always fresh
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

# =============================================================================
# Punto A8: Config Endpoints Refactored (Modular by Profile)
# =============================================================================

from app.schemas.config_schemas import (
    BrowserConfigUpdate,
    CoreConfigUpdate,
    TelnyxConfigUpdate,
    TwilioConfigUpdate,
)


@router.patch("/api/config/browser", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_browser_config(
    request: Request,
    config: BrowserConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update Browser/Simulator profile configuration.
    Refactored in B3 to use centralized config_utils.
    """
    try:
        from app.core.config_utils import update_env_file

        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)

        # Persist to .env
        updates = {}
        for key, value in update_data.items():
            updates[key.upper()] = value

        update_env_file(updates)

        return {
            "status": "success",
            "profile": "browser",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }

    except Exception as e:
        logger.error(f"Error updating Browser config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/api/config/twilio", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_twilio_config(
    request: Request,
    config: TwilioConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update Twilio/Phone profile configuration.
    Refactored in B3 to use centralized config_utils.
    """
    try:
        from app.core.config_utils import update_env_file

        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)

        # Persist to .env
        updates = {}
        for key, value in update_data.items():
            updates[key.upper()] = value

        update_env_file(updates)

        return {
            "status": "success",
            "profile": "twilio",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }

    except Exception as e:
        logger.error(f"Error updating Twilio config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/api/config/telnyx", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_telnyx_config(
    request: Request,
    config: TelnyxConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update Telnyx profile configuration.
    Refactored in B3 to use centralized config_utils.
    """
    try:
        from app.core.config_utils import update_env_file

        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)

        # Persist to .env
        updates = {}
        for key, value in update_data.items():
            updates[key.upper()] = value

        update_env_file(updates)

        return {
            "status": "success",
            "profile": "telnyx",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }

    except Exception as e:
        logging.error(f"Error updating Telnyx config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/api/config/core", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def update_core_config(
    request: Request,
    config: CoreConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update Core/Global configuration.
    Refactored in B3 to use centralized config_utils.
    """
    try:
        from app.core.config_utils import update_env_file

        update_data = config.dict(exclude_unset=True)
        await db_service.update_agent_config(db, **update_data)

        # Persist to .env
        updates = {}
        for key, value in update_data.items():
            updates[key.upper()] = value

        update_env_file(updates)

        return {
            "status": "success",
            "profile": "core",
            "updated_fields": list(update_data.keys()),
            "count": len(update_data)
        }

    except Exception as e:
        logging.error(f"Error updating Core config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

# =============================================================================
# DEPRECATED: Monolithic Endpoint (Punto A8)
# =============================================================================
# This endpoint is maintained for backward compatibility but is DEPRECATED.
# Use the modular endpoints above: /api/config/{browser|twilio|telnyx|core}
# This will be removed in v2.0
# =============================================================================

# =============================================================================
# FIELD NAME NORMALIZATION
# =============================================================================
# CRITICAL: UI uses camelCase, Schema uses snake_case
# This mapping ensures proper persistence of all configuration fields
FIELD_ALIASES = {
    # LLM Configuration
    'provider': 'llm_provider',
    'model': 'llm_model',
    'temp': 'temperature',
    'tokens': 'max_tokens',
    'prompt': 'system_prompt',
    'msg': 'first_message',
    'mode': 'first_message_mode',
    'mode': 'first_message_mode',
    # 'extractionModel': 'extraction_model', # DEPRECATED
    
    # TTS Configuration
    'voiceProvider': 'tts_provider',
    'voiceId': 'voice_name',
    'voiceStyle': 'voice_style',
    'voiceSpeed': 'voice_speed',
    'voicePacing': 'voice_pacing_ms',
    'voiceBgSound': 'background_sound',
    'voiceBgUrl': 'background_sound_url',
    'voiceLang': 'voice_language',  # NEW: Missing in schema, will need to be added
    
    # Conversation Style Configuration (NEW)
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
    'vadThreshold': 'vad_threshold', # Added alias for VAD slider
    
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
    
    # Quality & Latency (Advanced Refactor)
    'noiseSuppressionLevel': 'noise_suppression_level',
    'audioCodec': 'audio_codec',
    'enableBackchannel': 'enable_backchannel',
    'silenceTimeoutMs': 'silence_timeout_ms', # Mapped from slider
    'silenceTimeoutMsPhone': 'silence_timeout_ms_phone', # Mapped from slider
}

# =============================================================================
# AJAX/JSON Config Update Endpoint
# =============================================================================

@router.post("/api/config/update-json", dependencies=[Depends(verify_api_key)])
async def update_config_json(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        data = await request.json()
        logger.info(f"🔄 [CONFIG-JSON] Received update payload: {len(data)} keys")
        
        # Fetch current config
        current_config = await db_service.get_agent_config(db)
        
        # Iterate and Update with Field Normalization
        updated_count = 0
        normalized_count = 0
        
        for key, value in data.items():
            # Skip non-config metadata
            if key in ["id", "name", "created_at", "api_key"]:
                continue
            
            # CRITICAL: Normalize field names (UI camelCase → Schema snake_case)
            normalized_key = FIELD_ALIASES.get(key, key)
            if normalized_key != key:
                normalized_count += 1
                logger.debug(f"🔀 [NORMALIZE] {key} → {normalized_key}")
            
            # Check if key exists in model
            if hasattr(current_config, normalized_key):
                # Type Conversion Logic
                if value == "":
                    value = None
                
                # Type Conversion for AJAX Form Data (strings → proper types)
                if isinstance(value, str):
                    # Boolean Conversion
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    # Numeric Conversion
                    elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                
                setattr(current_config, normalized_key, value)
                updated_count += 1
            else:
                logger.warning(f"⚠️ [CONFIG-JSON] Ignored unknown key: {key} (normalized: {normalized_key})")

        await db.commit()
        await db.refresh(current_config)
        logger.info(f"✅ [CONFIG-JSON] Updated {updated_count} fields ({normalized_count} normalized).")
        
        # Validation Result
        warnings = []
        if hasattr(current_config, 'system_prompt') and current_config.system_prompt:
             unknowns = validate_prompt_variables(current_config.system_prompt)
             if unknowns:
                 warnings.append(f"Variables desconocidas en Prompt: {', '.join(unknowns)}")

        return {
            "status": "success", 
            "updated": updated_count, 
            "normalized": normalized_count,
            "warnings": warnings
        }
        
    except Exception as e:
        logger.error(f"❌ [CONFIG-JSON] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def validate_prompt_variables(prompt: str) -> list[str]:
    """
    Parses prompt for {{variable}} syntax and checks against known keys.
    Returns list of unknown variables.
    """
    import re
    if not prompt:
        return []
    
    # improved regex to catch {{ variable }} with spaces
    matches = re.findall(r'\{\{\s*(\w+)\s*\}\}', prompt)
    
    # Whitelist of Standard + Potential CRM Keys
    known_keys = {
        # Standard
        "name", "phone", "date", "time", "agent_name",
        # CRM/Debt Common
        "debt_amount", "due_date", "last_payment", "address", "email", "notes",
        # Baserow ID
        "baserow_row_id"
    }
    
    unknowns = [m for m in matches if m.lower() not in known_keys]
    return list(set(unknowns))

# =============================================================================
# LEGACY FORM ENDPOINT (Kept for backward compatibility if needed, else deprecate)
# =============================================================================
@router.post("/api/config/update", deprecated=True, dependencies=[Depends(verify_api_key)])
async def update_config(
    # Use str | None for EVERYTHING to prevent INT parsing errors on empty strings
    system_prompt: str = Form(None),
    temperature: str = Form(None), 
    voice_speed: str = Form(None),
    voice_speed_phone: str = Form(None), 
    voice_name: str = Form(None),
    voice_style: str = Form(None), 
    stt_language: str = Form(None), 
    llm_model: str = Form(None), 
    background_sound: str = Form(None), 
    idle_timeout: str = Form(None), 
    idle_message: str = Form(None), 
    inactivity_max_retries: str = Form(None), 
    max_duration: str = Form(None), 
    interruption_threshold: str = Form(None), 
    interruption_threshold_phone: str = Form(None), 

    # Audit Fixes Round 2 & 3
    hallucination_blacklist: str = Form(None),
    hallucination_blacklist_phone: str = Form(None),
    voice_pacing_ms: str = Form(None),
    voice_pacing_ms_phone: str = Form(None),
    voice_name_phone: str = Form(None),
    voice_style_phone: str = Form(None),
    input_min_characters_phone: str = Form(None),

    # Phone Model & Prompt
    system_prompt_phone: str = Form(None),
    first_message_phone: str = Form(None),
    first_message_mode_phone: str = Form(None),
    max_tokens_phone: str = Form(None),
    llm_provider_phone: str = Form(None),
    llm_model_phone: str = Form(None),
    stt_provider_phone: str = Form(None),
    stt_language_phone: str = Form(None),
    temperature_phone: str = Form(None),

    # Twilio Specific
    enable_denoising_phone: str = Form(None), 
    twilio_machine_detection: str = Form(None),
    twilio_record: str = Form(None),
    twilio_recording_channels: str = Form(None),
    twilio_trim_silence: str = Form(None),
    initial_silence_timeout_ms_phone: str = Form(None),

    # Telnyx Specific
    stt_provider_telnyx: str = Form(None),
    stt_language_telnyx: str = Form(None),
    llm_provider_telnyx: str = Form(None),
    llm_model_telnyx: str = Form(None),
    system_prompt_telnyx: str = Form(None),
    voice_name_telnyx: str = Form(None),
    voice_style_telnyx: str = Form(None),
    temperature_telnyx: str = Form(None),
    first_message_telnyx: str = Form(None),
    first_message_mode_telnyx: str = Form(None),
    max_tokens_telnyx: str = Form(None),
    initial_silence_timeout_ms_telnyx: str = Form(None),
    input_min_characters_telnyx: str = Form(None),
    enable_denoising_telnyx: str = Form(None),
    voice_pacing_ms_telnyx: str = Form(None),
    silence_timeout_ms_telnyx: str = Form(None),
    interruption_threshold_telnyx: str = Form(None),
    hallucination_blacklist_telnyx: str = Form(None),
    voice_speed_telnyx: str = Form(None),
    voice_sensitivity_telnyx: str = Form(None),
    enable_krisp_telnyx: str = Form(None),
    enable_vad_telnyx: str = Form(None),

    # Telnyx Advanced
    idle_timeout_telnyx: str = Form(None),
    max_duration_telnyx: str = Form(None),
    idle_message_telnyx: str = Form(None),
    enable_recording_telnyx: str = Form(None),
    amd_config_telnyx: str = Form(None),

    # 🔒 LOCKED: MODEL & CORE ARGS
    first_message: str = Form(None),
    first_message_mode: str = Form(None),
    max_tokens: str = Form(None),
    voice_id_manual: str = Form(None),
    background_sound_url: str = Form(None),
    input_min_characters: str = Form(None),

    # Stage 2: Transcriber
    silence_timeout_ms: str = Form(None),
    silence_timeout_ms_phone: str = Form(None), 
    segmentation_max_time: str = Form(None),
    segmentation_strategy: str = Form(None), # Restored: Smart Interruption Toggle
    
    # VAD Settings (Added in Transcriptor Audit)
    vad_threshold: str = Form(None),

    enable_denoising: str = Form(None), 
    initial_silence_timeout_ms: str = Form(None), 
    # punctuation_boundaries: str = Form(None), # DEPRECATED 

    # 🔒 LOCKED: TRANSCRIBING & FUNCTIONS
    enable_end_call: str = Form(None),
    enable_dial_keypad: str = Form(None),
    transfer_phone_number: str = Form(None),

    stt_provider: str = Form(None),
    llm_provider: str = Form(None),
    tts_provider: str = Form(None),
    # extraction_model: str = Form(None), # DEPRECATED

    # Browser - Conversation Style
    response_length: str = Form(None),
    conversation_tone: str = Form(None),
    conversation_formality: str = Form(None),
    conversation_pacing: str = Form(None),

    # Phone - Conversation Style
    response_length_phone: str = Form(None),
    conversation_tone_phone: str = Form(None),
    conversation_formality_phone: str = Form(None),
    conversation_pacing_phone: str = Form(None),

    # Telnyx - Conversation Style
    response_length_telnyx: str = Form(None),
    conversation_tone_telnyx: str = Form(None),
    conversation_formality_telnyx: str = Form(None),
    conversation_pacing_telnyx: str = Form(None),
    
    # Quality & Latency
    noise_suppression_level: str = Form(None),
    audio_codec: str = Form(None),
    enable_backchannel: str = Form(None),

    db: AsyncSession = Depends(get_db)
):
    try:
        def parse_float(v):
            try: return float(v) if v else None
            except: return None
        
        def parse_int(v):
            try: return int(v) if v else None
            except: return None
            
        def parse_bool(v):
            if not v: return None
            return str(v).lower() in ("true", "1", "yes", "on")

        # Clean Data
        update_data = {
            "system_prompt": system_prompt,
            "temperature": parse_float(temperature),
            "voice_speed": parse_float(voice_speed),
            "voice_speed_phone": parse_float(voice_speed_phone),
            "voice_name": voice_name,
            "voice_style": voice_style,
            "stt_language": stt_language,
            "llm_model": llm_model,
            "background_sound": background_sound,
            "idle_timeout": parse_float(idle_timeout),
            "idle_message": idle_message,
            "inactivity_max_retries": parse_int(inactivity_max_retries),
            "max_duration": parse_int(max_duration),
            "interruption_threshold": parse_int(interruption_threshold),
            "interruption_threshold_phone": parse_int(interruption_threshold_phone),
            "hallucination_blacklist": hallucination_blacklist,
            "hallucination_blacklist_phone": hallucination_blacklist_phone,
            "voice_pacing_ms": parse_int(voice_pacing_ms),
            "voice_pacing_ms_phone": parse_int(voice_pacing_ms_phone),
            "voice_name_phone": voice_name_phone,
            "voice_style_phone": voice_style_phone,
            "input_min_characters_phone": parse_int(input_min_characters_phone),
            
            "system_prompt_phone": system_prompt_phone,
            "first_message_phone": first_message_phone,
            "first_message_mode_phone": first_message_mode_phone,
            "max_tokens_phone": parse_int(max_tokens_phone),
            "llm_provider_phone": llm_provider_phone,
            "llm_model_phone": llm_model_phone,
            "stt_provider_phone": stt_provider_phone,
            "stt_language_phone": stt_language_phone,
            "temperature_phone": parse_float(temperature_phone),
            
            "enable_denoising_phone": parse_bool(enable_denoising_phone),
            "twilio_machine_detection": twilio_machine_detection,
            "twilio_record": parse_bool(twilio_record),
            "twilio_recording_channels": twilio_recording_channels,
            "twilio_trim_silence": parse_bool(twilio_trim_silence),
            "initial_silence_timeout_ms_phone": parse_int(initial_silence_timeout_ms_phone),

            "stt_provider_telnyx": stt_provider_telnyx,
            "stt_language_telnyx": stt_language_telnyx,
            "llm_provider_telnyx": llm_provider_telnyx,
            "llm_model_telnyx": llm_model_telnyx,
            "system_prompt_telnyx": system_prompt_telnyx,
            "voice_name_telnyx": voice_name_telnyx,
            "voice_style_telnyx": voice_style_telnyx,
            "temperature_telnyx": parse_float(temperature_telnyx),
            "first_message_telnyx": first_message_telnyx,
            "first_message_mode_telnyx": first_message_mode_telnyx,
            "max_tokens_telnyx": parse_int(max_tokens_telnyx),
            "initial_silence_timeout_ms_telnyx": parse_int(initial_silence_timeout_ms_telnyx),
            "input_min_characters_telnyx": parse_int(input_min_characters_telnyx),
            "enable_denoising_telnyx": parse_bool(enable_denoising_telnyx),
            "voice_pacing_ms_telnyx": parse_int(voice_pacing_ms_telnyx),
            "silence_timeout_ms_telnyx": parse_int(silence_timeout_ms_telnyx),
            "interruption_threshold_telnyx": parse_int(interruption_threshold_telnyx),
            "hallucination_blacklist_telnyx": hallucination_blacklist_telnyx,
            "voice_speed_telnyx": parse_float(voice_speed_telnyx),
            "voice_sensitivity_telnyx": parse_int(voice_sensitivity_telnyx),
            "enable_krisp_telnyx": parse_bool(enable_krisp_telnyx),
            "noise_suppression_level": noise_suppression_level,
            "audio_codec": audio_codec,
            "enable_backchannel": parse_bool(enable_backchannel),
            "enable_vad_telnyx": parse_bool(enable_vad_telnyx),
            
            "idle_timeout_telnyx": parse_float(idle_timeout_telnyx),
            "max_duration_telnyx": parse_int(max_duration_telnyx),
            "idle_message_telnyx": idle_message_telnyx,
            "enable_recording_telnyx": parse_bool(enable_recording_telnyx),
            "amd_config_telnyx": amd_config_telnyx,

            "first_message": first_message,
            "first_message_mode": first_message_mode,
            "max_tokens": parse_int(max_tokens),
            "voice_id_manual": voice_id_manual,
            "background_sound_url": background_sound_url,
            "input_min_characters": parse_int(input_min_characters),
            
            "silence_timeout_ms": parse_int(silence_timeout_ms),
            "silence_timeout_ms_phone": parse_int(silence_timeout_ms_phone),
            "segmentation_max_time": parse_int(segmentation_max_time),
            "segmentation_strategy": segmentation_strategy,
            "vad_threshold": parse_float(vad_threshold),
            "enable_denoising": parse_bool(enable_denoising),
            "initial_silence_timeout_ms": parse_int(initial_silence_timeout_ms),
            # "punctuation_boundaries": punctuation_boundaries, # DEPRECATED
            
            "enable_end_call": parse_bool(enable_end_call),
            "enable_dial_keypad": parse_bool(enable_dial_keypad),
            "transfer_phone_number": transfer_phone_number,

            "stt_provider": stt_provider,
            "llm_provider": llm_provider,
            "tts_provider": tts_provider,
            # "extraction_model": extraction_model, # DEPRECATED

            # Conversation Style - Browser
            "response_length": response_length,
            "conversation_tone": conversation_tone,
            "conversation_formality": conversation_formality,
            "conversation_pacing": conversation_pacing,

            # Conversation Style - Phone
            "response_length_phone": response_length_phone,
            "conversation_tone_phone": conversation_tone_phone,
            "conversation_formality_phone": conversation_formality_phone,
            "conversation_pacing_phone": conversation_pacing_phone,

            # Conversation Style - Telnyx
            "response_length_telnyx": response_length_telnyx,
            "conversation_tone_telnyx": conversation_tone_telnyx,
            "conversation_formality_telnyx": conversation_formality_telnyx,
            "conversation_pacing_telnyx": conversation_pacing_telnyx,
        }

        final_data = {k: v for k, v in update_data.items() if v is not None}
        await db_service.update_agent_config(db, **final_data)

        # Persist to .env (Best Effort)
        try:
            from app.core.config_utils import update_env_file
            updates = {k.upper(): v for k, v in final_data.items()}
            update_env_file(updates)
        except Exception as e:
            logging.warning(f"Could not update .env file (likely read-only permission): {e}")

        return RedirectResponse(url="/dashboard?success=true", status_code=303)
    
    except Exception as e:
        import traceback
        logging.error(f"Error updating config: {e}")
        logging.error(traceback.format_exc())
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e), "trace": traceback.format_exc()})

@router.post("/api/config/patch", dependencies=[Depends(verify_api_key)])
async def patch_config(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Accepts JSON payload to update specific config fields.
    Example: {"input_min_characters": 30}
    """
    try:
        data = await request.json()

        # Type Conversion Helper
        # Ensure we cast known int/float fields to avoid DB errors (AsyncPG is strict)
        int_fields = [
            "input_min_characters", "max_tokens", "silence_timeout_ms",
            "initial_silence_timeout_ms", "segmentation_max_time",
            "interruption_threshold", "interruption_threshold_phone",
            "silence_timeout_ms_phone", "max_duration",
            "max_tokens_telnyx", "initial_silence_timeout_ms_telnyx", "input_min_characters_telnyx",
            "voice_pacing_ms_telnyx", "silence_timeout_ms_telnyx", "interruption_threshold_telnyx",
            "inactivity_max_retries"
        ]
        float_fields = [
            "temperature", "voice_speed", "voice_speed_phone", "idle_timeout",
            "temperature_telnyx", "voice_speed_telnyx"
        ]
        bool_fields = [
             "enable_denoising", "enable_end_call", "enable_dial_keypad",
             "enable_denoising_telnyx"
        ]

        cleaned_data = {}
        for k, v in data.items():
            if v is None:
                cleaned_data[k] = None
                continue

            if k in int_fields:
                cleaned_data[k] = int(v)
            elif k in float_fields:
                cleaned_data[k] = float(v)
            elif k in bool_fields:
                # Handle JS booleans or strings "true"/"false"
                if isinstance(v, bool):
                    cleaned_data[k] = v
                else:
                    cleaned_data[k] = str(v).lower() == 'true'
            else:
                cleaned_data[k] = v

        await db_service.update_agent_config(db, **cleaned_data)
        return {"status": "success", "updated": cleaned_data}
    except Exception as e:
        logging.error(f"Config Patch Failed: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/dashboard/call/{call_id}", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def dashboard_call_detail(request: Request, call_id: int, db: AsyncSession = Depends(get_db)):
    try:
        call = await db_service.get_call_details(db, call_id)
        if not call:
             # Fallback for invalid ID
             return RedirectResponse("/dashboard?error=call_not_found")
        
        return templates.TemplateResponse("call_details.html", {
            "request": request,
            "call": call
        })
    except Exception as e:
        logger.error(f"Error fetching call details: {e}")
        return RedirectResponse("/dashboard?error=details_error")


# =============================================================================
# HISTORY API ENDPOINTS (Implementación Funcional)
# =============================================================================

@router.get("/api/history/rows", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def get_history_rows(request: Request, db: AsyncSession = Depends(get_db)):
    """
    HTMX Endpoint: Returns just the <tr> rows for the history table.
    """
    history = await db_service.get_recent_calls(session=db, limit=20)
    
    # We render a partial template or use a macro. 
    # For simplicity, we assume the dashboard.html loop logic is reusable 
    # OR we return a fragment.
    # Ideally, we should have 'partials/history_rows.html'.
    # For now, we manually construct or reuse the full page? No, too heavy.
    # Let's use a small inline template string or partial file.
    # Given the constraint, I'll attempt to use a partial if it exists (step 1343 hinted 'partials/tab_history.html' might exist?)
    # Wait, Step 1343 grep showed 'app/templates/partials/tab_history.html'.
    # If that exists, we can render it? No, that's likely the full tab.
    # We need just the rows.
    
    # Quick fix: Inline Jinja for rows.
    row_template = """
    {% for call in history %}
    <tr class="border-b border-slate-800 hover:bg-slate-800/50"
        x-show="activeHistoryFilter === 'all' || activeHistoryFilter === '{{ call.client_type or 'browser' }}'">
        <td class="px-4 py-2">
            <input type="checkbox" value="{{ call.id }}"
                class="history-checkbox rounded bg-slate-700 border-slate-600 text-blue-600 focus:ring-blue-600 ring-offset-slate-800 focus:ring-2"
                onchange="updateDeleteButton()">
        </td>
        <td class="px-4 py-2 font-mono">{{ call.start_time.strftime('%Y-%m-%d %H:%M') }}</td>
        <td class="px-4 py-2">
            {% if call.client_type == 'telnyx' %}
            <span class="px-2 py-0.5 rounded bg-emerald-900/40 text-emerald-400 border border-emerald-700/50">Telnyx</span>
            {% elif call.client_type == 'twilio' %}
            <span class="px-2 py-0.5 rounded bg-red-900/40 text-red-400 border border-red-700/50">Twilio</span>
            {% else %}
            <span class="px-2 py-0.5 rounded bg-blue-900/40 text-blue-400 border border-blue-700/50">Simulador</span>
            {% endif %}
        </td>
        <td class="px-4 py-2 font-mono">
            {% if call.end_time %}
            {{ (call.end_time - call.start_time).seconds }}s
            {% else %}
            <span class="text-yellow-500 animate-pulse">En curso</span>
            {% endif %}
        </td>
        <td class="px-4 py-2">
            <a href="/dashboard/call/{{ call.id }}?api_key={{ request.query_params.get('api_key', '') }}"
                class="text-blue-400 hover:underline">Ver</a>
        </td>
    </tr>
    {% endfor %}
    {% if not history %}
    <tr>
        <td colspan="5" class="px-4 py-8 text-center text-slate-500 italic">
            No hay historial disponible.
        </td>
    </tr>
    {% endif %}
    """
    from jinja2 import Template
    t = Template(row_template)
    content = t.render(history=history, request=request)
    return HTMLResponse(content)

@router.post("/api/history/clear", dependencies=[Depends(verify_api_key)])
async def clear_history(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Clear entire history.
    """
    await db_service.clear_all_history(db)
    return RedirectResponse("/dashboard?success=history_cleared", status_code=303)



@router.get("/api/history/rows", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def history_rows(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    try:
        offset = (page - 1) * limit
        history = await db_service.get_recent_calls(db, limit=limit, offset=offset)
        total = await db_service.get_total_calls(db)
        if total is None:
            total = 0
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        return templates.TemplateResponse("partials/history_panel.html", {
            "request": request,
            "history": history,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_items": total,
            "models": {
                "groq": [
                    {"id": "llama-3.3-70b-versatile"},
                    {"id": "llama-3.1-70b-versatile"},
                    {"id": "llama-3.1-8b-instant"}
                ],
                "azure": [
                    {"id": "gpt-4o"},
                    {"id": "gpt-3.5-turbo"}
                ]
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"<tr><td colspan='5' class='p-4 text-center text-red-400 font-bold'>Error cargando historial: {e}</td></tr>")

@router.post("/api/history/delete-selected", dependencies=[Depends(verify_api_key)])
async def delete_selected(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
        call_ids = data.get("call_ids", [])
        if not call_ids:
            return {"status": "error", "message": "No IDs provided"}

        await db_service.delete_calls(db, call_ids)
        return {"status": "success", "count": len(call_ids)}
    except Exception as e:
        logging.error(f"Error deleting calls: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/api/history/clear", dependencies=[Depends(verify_api_key)])
async def clear_history(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        await db_service.clear_all_history(db)
        return RedirectResponse("/dashboard?tab=historial&api_key=" + (request.query_params.get("api_key") or ""), status_code=303)
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        # Redirect back with error
        return RedirectResponse("/dashboard?error=clear_failed", status_code=303)


@router.post("/api/voice/preview", dependencies=[Depends(verify_api_key)])
async def preview_voice(
    voice_name: str = Form(...),
    voice_speed: float = Form(1.0),
    voice_pitch: int = Form(0),
    voice_volume: int = Form(100),
    voice_style: str = Form(None),
    voice_style_degree: float = Form(1.0)
):
    """
    Generate voice preview with current configuration.
    Returns audio file for immediate playback.
    """
    try:
        from app.utils.ssml_builder import build_azure_ssml
        from app.providers.azure import AzureProvider
        
        # Build SSML with parameters
        ssml = build_azure_ssml(
            voice_name=voice_name,
            text="Hola, esta es una muestra de mi voz con la configuración actual.",
            rate=voice_speed,
            pitch=voice_pitch,
            volume=voice_volume,
            style=voice_style if voice_style and voice_style.strip() else None,
            style_degree=voice_style_degree
        )
        
        logger.info(f"🎤 Preview request: voice={voice_name}, speed={voice_speed}, pitch={voice_pitch}")
        
        # Synthesize audio
        azure_provider = AzureProvider()
        synthesizer = azure_provider.create_synthesizer(voice_name, "browser")
        audio_bytes = azure_provider.synthesize_ssml(synthesizer, ssml)
        
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        # Return audio
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=voice_preview.wav",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"❌ Voice preview error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to generate preview: {str(e)}"}
        )

