import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession  # NEW
from pydantic import BaseModel
from typing import Optional, Any

from app.core.auth_simple import verify_api_key
from app.core.input_sanitization import (
    register_template_filters,
)
from app.db.database import get_db  # NEW
from app.services.db_service import db_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

# Rate limiter for dashboard endpoints (Security - H-3)
limiter = Limiter(key_func=get_remote_address)

# Register sanitization filters for XSS protection (Punto A5)
template_filters = register_template_filters(None)
templates.env.filters.update(template_filters)

@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
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

    # Models
    llm_provider = GroqProvider()
    groq_models_raw = await llm_provider.get_available_models()
    # Normalize: Ensure list of dicts
    groq_models = [{"id": m, "name": m} if isinstance(m, str) else m for m in groq_models_raw]
    
    # Structure models for frontend: { 'groq': [...], 'azure': [...] }
    models = {
        "groq": groq_models,
        "azure": [
            {"id": "gpt-4o", "name": "GPT-4o (Omni)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-35-turbo", "name": "GPT-3.5 Turbo"}
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

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "config": config_dict,
        "voices": voices,
        "voice_styles": voice_styles,
        "languages": languages,
        "llm_models": models,
        "history": history_list,
        "protocol": request.url.scheme,
        "host": request.url.netloc
    })

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



# NEW: AJAX/JSON Endpoint
@router.post("/api/config/update-json", dependencies=[Depends(verify_api_key)])
async def update_config_json(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        data = await request.json()
        logger.info(f"🔄 [CONFIG-JSON] Received update payload: {len(data)} keys")
        
        # Security: Allow specific fields only? 
        # For now, we trust the schema matches AgentConfig columns.
        
        # Fetch current config
        current_config = await db_service.get_agent_config(db)
        
        # Iterate and Update
        updated_count = 0
        for key, value in data.items():
            # Skip non-config metadata
            if key in ["id", "name", "created_at"]:
                continue
                
            # Check if key exists in model
            if hasattr(current_config, key):
                # Type Conversion Logic (Basic)
                # Frontend sends correct types mostly, but handle strings->numbers if needed
                # For JSON, we assume types are correct (e.g. integer 5 sent as 5, not "5")
                # But empty strings "" should be None for nullable fields
                if value == "":
                    value = None
                    
                setattr(current_config, key, value)
                updated_count += 1
            else:
                logger.warning(f"⚠️ [CONFIG-JSON] Ignored unknown key: {key}")

        await db.commit()
        await db.refresh(current_config)
        logger.info(f"✅ [CONFIG-JSON] Updated {updated_count} fields.")
        
        return {"status": "success", "updated": updated_count, "config": current_config}
        
    except Exception as e:
        logger.error(f"❌ [CONFIG-JSON] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    segmentation_strategy: str = Form(None),
    enable_denoising: str = Form(None), 
    initial_silence_timeout_ms: str = Form(None), 
    punctuation_boundaries: str = Form(None), 

    # 🔒 LOCKED: TRANSCRIBING & FUNCTIONS
    enable_end_call: str = Form(None),
    enable_dial_keypad: str = Form(None),
    transfer_phone_number: str = Form(None),

    stt_provider: str = Form(None),
    llm_provider: str = Form(None),
    tts_provider: str = Form(None),
    extraction_model: str = Form(None),
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
            "enable_denoising": parse_bool(enable_denoising),
            "initial_silence_timeout_ms": parse_int(initial_silence_timeout_ms),
            "punctuation_boundaries": punctuation_boundaries,
            
            "enable_end_call": parse_bool(enable_end_call),
            "enable_dial_keypad": parse_bool(enable_dial_keypad),
            "transfer_phone_number": transfer_phone_number,

            "stt_provider": stt_provider,
            "llm_provider": llm_provider,
            "tts_provider": tts_provider,
            "extraction_model": extraction_model,
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

@router.get("/dashboard/history-rows", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
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

