import json
import logging
import re
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.tts.azure_tts_adapter import AzureTTSAdapter
from app.core.auth_simple import verify_api_key, verify_dashboard_access
from app.core.config import settings
from app.core.input_sanitization import register_template_filters
from app.db.database import get_db
from app.services.cache import cache
from app.services.db_service import db_service
from app.utils.ssml_builder import build_azure_ssml

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

# Rate limiter for dashboard endpoints (Security)
limiter = Limiter(key_func=get_remote_address)

# Register sanitization filters for XSS protection
template_filters = register_template_filters(None)
templates.env.filters.update(template_filters)

# =============================================================================
# CONSTANTS & MAPPINGS
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

    # Conversation Style Configuration
    'responseLength': 'response_length',
    'conversationTone': 'conversation_tone',
    'conversationFormality': 'conversation_formality',
    'conversationPacing': 'conversation_pacing',

    # STT Configuration
    'sttProvider': 'stt_provider',
    'sttLang': 'stt_language',
    'interruptWords': 'interruption_threshold',
    'interruptRMS': 'voice_sensitivity',  # Generic / Simulator
    'interruptRMSTelnyx': 'voice_sensitivity_telnyx',  # Explicit Telnyx
    'silence': 'silence_timeout_ms',
    'blacklist': 'hallucination_blacklist',
    'inputMin': 'input_min_characters',
    'vadThreshold': 'vad_threshold',
    'sttUtteranceEnd': 'stt_utterance_end_strategy',
    'sttKeywords': 'stt_keywords',
    'sttPunctuation': 'stt_punctuation',
    'sttSmartFormatting': 'stt_smart_formatting',
    'sttProfanityFilter': 'stt_profanity_filter',
    'sttDiarization': 'stt_diarization',
    'sttMultilingual': 'stt_multilingual',

    # Advanced Features
    'denoise': 'enable_denoising',
    'krisp': 'enable_krisp_telnyx',
    'vad': 'enable_vad_telnyx',
    'maxDuration': 'max_duration',
    'maxRetries': 'inactivity_max_retries',
    'idleTimeout': 'idle_timeout',
    'idleMessage': 'idle_message',
    'enableRecording': 'enable_recording_telnyx',
    'enableEndCall': 'enable_end_call',
    'dialKeypad': 'enable_dial_keypad',
    'transferNum': 'transfer_phone_number',

    # TOOLS & ACTIONS (PHASE VI)
    'toolsSchema': 'tools_schema',
    'asyncTools': 'tools_async',
    'clientToolsEnabled': 'client_tools_enabled',
    'toolServerUrl': 'tool_server_url',
    'toolServerSecret': 'tool_server_secret',
    'toolTimeoutMs': 'tool_timeout_ms',
    'toolRetryCount': 'tool_retry_count',
    'toolErrorMsg': 'tool_error_msg',
    'redactParams': 'redact_params',
    'transferWhitelist': 'transfer_whitelist',
    'stateInjectionEnabled': 'state_injection_enabled',

    # INTEGRATIONS (CRM & Webhook)
    'crmEnabled': 'crm_enabled',
    'webhookUrl': 'webhook_url',
    'webhookSecret': 'webhook_secret',

    # CONNECTIVITY & TELEPHONY (PHASE V)
    # 1. Credentials (BYOC)
    'twilioAccountSid': 'twilio_account_sid',
    'twilioAuthToken': 'twilio_auth_token',
    'twilioFromNumber': 'twilio_from_number',
    'telnyxApiKey': 'telnyx_api_key',
    'telnyxConnectionId': 'telnyx_connection_id',

    # 2. SIP & Infrastructure
    'callerIdPhone': 'caller_id_phone',
    'sipTrunkUriPhone': 'sip_trunk_uri_phone',
    'sipAuthUserPhone': 'sip_auth_user_phone',
    'sipAuthPassPhone': 'sip_auth_pass_phone',
    'fallbackNumberPhone': 'fallback_number_phone',
    'geoRegionPhone': 'geo_region_phone',

    'callerIdTelnyx': 'caller_id_telnyx',
    'sipTrunkUriTelnyx': 'sip_trunk_uri_telnyx',
    'sipAuthUserTelnyx': 'sip_auth_user_telnyx',
    'sipAuthPassTelnyx': 'sip_auth_pass_telnyx',
    'fallbackNumberTelnyx': 'fallback_number_telnyx',
    'geoRegionTelnyx': 'geo_region_telnyx',

    # 3. Recording & Compliance
    'recordingChannelsPhone': 'recording_channels_phone',
    'recordingEnabledPhone': 'recording_enabled_phone',
    'recordingChannelsTelnyx': 'recording_channels_telnyx',
    'enableRecordingTelnyx': 'enable_recording_telnyx',

    'hipaaEnabledPhone': 'hipaa_enabled_phone',
    'hipaaEnabledTelnyx': 'hipaa_enabled_telnyx',

    'dtmfListeningEnabledPhone': 'dtmf_listening_enabled_phone',
    'dtmfListeningEnabledTelnyx': 'dtmf_listening_enabled_telnyx',

    # SYSTEM & GOVERNANCE (PHASE VIII)
    'concurrencyLimit': 'concurrency_limit',
    'spendLimitDaily': 'spend_limit_daily',
    'environment': 'environment',
    'privacyMode': 'privacy_mode',
    'auditLogEnabled': 'audit_log_enabled',

    # ADVANCED: QUALITY & LIMITS (PHASE IX)
    'noiseSuppressionLevel': 'noise_suppression_level',
    'audioCodec': 'audio_codec',
    'enableBackchannel': 'enable_backchannel',

    # Quality & Latency
    'silenceTimeoutMs': 'silence_timeout_ms',
    'silenceTimeoutMsPhone': 'silence_timeout_ms_phone',
}

# =============================================================================
# LOGIN ROUTES
# =============================================================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("authenticated"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def login_submit(request: Request, api_key: str = Form(...)):
    valid_key = getattr(settings, 'ADMIN_API_KEY', None)

    if valid_key and secrets.compare_digest(api_key, valid_key):
        request.session["authenticated"] = True
        logger.info(f"✅ User logged in via Dashboard Login from {request.client.host}")
        return RedirectResponse("/dashboard", status_code=302)

    logger.warning(f"❌ Failed login attempt from {request.client.host}")
    return templates.TemplateResponse("login.html", {"request": request, "error": "Clave Incorrecta"})

# =============================================================================
# DASHBOARD MAIN ROUTE
# =============================================================================

@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(verify_dashboard_access)])
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    config = await db_service.get_agent_config(db)

    # Voices
    tts_adapter = AzureTTSAdapter() # Lightweight init

    # Languages
    azure_langs = tts_adapter.get_available_languages()
    languages = {
        "azure": azure_langs
    }

    voice_styles = tts_adapter.get_voice_styles("es-MX-DaliaNeural") # Default example or empty

    # Models - CURATED lists
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

    # Voices - Try cache first (24h TTL)
    voices = await cache.get("voices_metadata")

    if not voices:
        logger.info("🔄 Loading voices from Azure (cache miss)")
        voices = {"azure": {}}
        azure_voices_objects = tts_adapter.get_available_voices()

        for v in azure_voices_objects:
            locale = v.locale
            if not locale:
                continue

            if locale not in voices["azure"]:
                voices["azure"][locale] = []

            voices["azure"][locale].append({
                "id": v.id,
                "name": v.name,
                "gender": v.gender.lower()
            })

        # Fallback
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

        await cache.set("voices_metadata", voices, ttl=86400)
    else:
        logger.info("🎯 Voices loaded from cache")
        await cache.set("voices_metadata", voices, ttl=86400)

    # Styles - Try cache
    voice_styles_cached = await cache.get("voice_styles")
    if not voice_styles_cached:
        # We need the full styles map for the frontend
        # Assuming we added this method to adapter
        voice_styles = tts_adapter.get_all_voice_styles()
        await cache.set("voice_styles", voice_styles, ttl=86400)
    else:
        voice_styles = voice_styles_cached

    history = await db_service.get_recent_calls(session=db, limit=10)

    # Helpers for serialization
    def model_to_dict(obj):
        if not obj:
            return {}
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    config_dict = model_to_dict(config)
    history_list = [model_to_dict(call) for call in history]

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

    # Prevent caching
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

# =============================================================================
# CONFIG ENDPOINTS (JSON)
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

        updated_count = 0
        normalized_count = 0

        for key, value in data.items():
            # Skip non-config metadata
            if key in ["id", "name", "created_at", "api_key"]:
                continue

            # Normalize field names
            normalized_key = FIELD_ALIASES.get(key, key)
            if normalized_key != key:
                normalized_count += 1
                logger.debug(f"🔀 [NORMALIZE] {key} → {normalized_key}")

            # Check if key exists in model
            if hasattr(current_config, normalized_key):
                normalized_value = value
                # Sanitize Empty Strings
                if normalized_value == "":
                    normalized_value = None

                # Type Conversion for AJAX Form Data
                if isinstance(normalized_value, str):
                    if normalized_value.lower() == 'true':
                        normalized_value = True
                    elif normalized_value.lower() == 'false':
                        normalized_value = False
                    elif normalized_value.replace('.', '', 1).replace('-', '', 1).isdigit():
                        normalized_value = float(normalized_value) if "." in normalized_value else int(normalized_value)

                setattr(current_config, normalized_key, normalized_value)
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
        raise HTTPException(status_code=500, detail=str(e)) from e

def validate_prompt_variables(prompt: str) -> list[str]:
    """
    Parses prompt for {{variable}} syntax and checks against known keys.
    Returns list of unknown variables.
    """
    if not prompt:
        return []

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
# CALL DETAILS
# =============================================================================

@router.get("/dashboard/call/{call_id}", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def dashboard_call_detail(request: Request, call_id: int, db: AsyncSession = Depends(get_db)):
    try:
        call = await db_service.get_call_details(db, call_id)
        if not call:
             return RedirectResponse("/dashboard?error=call_not_found")

        return templates.TemplateResponse("call_details.html", {
            "request": request,
            "call": call
        })
    except Exception as e:
        logger.error(f"Error fetching call details: {e}", exc_info=True)
        return RedirectResponse("/dashboard?error=details_error")

# =============================================================================
# HISTORY API ENDPOINTS
# =============================================================================

@router.get("/api/history/rows", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def history_rows(request: Request, page: int = 1, limit: int = 20, db: AsyncSession = Depends(get_db)):
    try:
        offset = (page - 1) * limit
        history = await db_service.get_recent_calls(db, limit=limit, offset=offset)
        total = await db_service.get_total_calls(db)
        if total is None:
            total = 0
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        return templates.TemplateResponse("partials/history_rows.html", {
            "request": request,
            "history": history,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_items": total
        })
    except Exception as e:
        logger.error(f"Error loading history rows: {e}", exc_info=True)
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
        logger.error(f"Error deleting calls: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/api/history/clear", dependencies=[Depends(verify_api_key)])
async def clear_history(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Clear entire history.
    """
    try:
        await db_service.clear_all_history(db)
        return RedirectResponse("/dashboard?tab=historial&api_key=" + (request.query_params.get("api_key") or ""), status_code=303)
    except Exception as e:
        logger.error(f"Error clearing history: {e}", exc_info=True)
        return RedirectResponse("/dashboard?error=clear_failed", status_code=303)

# =============================================================================
# VOICE PREVIEW
# =============================================================================

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
    Result: WAV audio file.
    """
    try:
        ssml = build_azure_ssml(
            voice_name=voice_name,
            text="Hola, esta es una muestra de mi voz con la configuración actual.",
            rate=voice_speed,
            pitch=voice_pitch,
            volume=voice_volume,
            style=voice_style if voice_style and voice_style.strip() else None,
            style_degree=voice_style_degree
        )

        logging.info(f"🎤 Preview request: voice={voice_name}, speed={voice_speed}, pitch={voice_pitch}")

        # Synthesize audio
        azure_adapter = AzureTTSAdapter(audio_mode="browser")
        audio_bytes = await azure_adapter.synthesize_ssml(ssml)

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio")

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=voice_preview.wav",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"❌ Voice preview error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to generate preview: {e!s}"}
        )
