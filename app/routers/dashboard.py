from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.db_service import db_service
from app.core.service_factory import ServiceFactory
from app.db.models import AgentConfig
import logging

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = await db_service.get_agent_config()
    
    # Fetch Dynamic Options
    # Use temporary instances or factory if possible.
    # We can instantiate providers directly to get static lists if methods are static/or lightweight
    from app.providers.azure import AzureProvider
    from app.providers.groq import GroqProvider
    
    # Voices
    tts_provider = AzureProvider() # Lightweight init
    voices = tts_provider.get_available_voices()
    voice_styles = tts_provider.get_voice_styles() # New
    languages = tts_provider.get_available_languages()
    
    # Models
    llm_provider = GroqProvider()
    models = await llm_provider.get_available_models()
    
    history = await db_service.get_recent_calls(limit=10) # New
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "config": config,
        "voices": voices,
        "voice_styles": voice_styles,
        "languages": languages,
        "llm_models": models, # Renamed for clarity in template
        "history": history, # New
        "protocol": request.url.scheme,
        "host": request.url.netloc
    })

@router.post("/api/config/update")
async def update_config(
    system_prompt: str = Form(...),
    temperature: float = Form(...), # Restore temperature
    voice_speed: float = Form(...),
    voice_speed_phone: float = Form(0.9), # New
    voice_name: str = Form("es-MX-DaliaNeural"), 
    voice_style: str = Form(None), # New
    stt_language: str = Form("es-MX"), # New
    llm_model: str = Form("llama-3.3-70b-versatile"), # New
    background_sound: str = Form("none"), # New
    idle_timeout: float = Form(10.0), # New
    idle_message: str = Form("¿Hola? ¿Sigue ahí?"), # New
    max_duration: int = Form(600), # New
    interruption_threshold: int = Form(5), # New
    interruption_threshold_phone: int = Form(2), # New

    # Audit Fixes Round 2 & 3
    hallucination_blacklist: str = Form("Pero.,Y...,Mm.,Oye.,Ah."),
    hallucination_blacklist_phone: str = Form("Pero.,Y...,Mm.,Oye.,Ah."),
    voice_pacing_ms: int = Form(300),
    voice_pacing_ms_phone: int = Form(500),
    voice_name_phone: str = Form(None),
    voice_style_phone: str = Form(None),
    input_min_characters_phone: int = Form(4),
    
    # Phone Model & Prompt
    system_prompt_phone: str = Form(None),
    first_message_phone: str = Form(None),
    first_message_mode_phone: str = Form("speak-first"),
    max_tokens_phone: int = Form(250),
    llm_provider_phone: str = Form("groq"),
    llm_model_phone: str = Form(None),
    stt_provider_phone: str = Form("azure"),
    stt_language_phone: str = Form("es-US"),
    temperature_phone: float = Form(0.7),
    
    # Twilio Specific
    enable_denoising_phone: bool = Form(True),
    twilio_machine_detection: str = Form("Enable"),
    twilio_record: bool = Form(False),
    twilio_recording_channels: str = Form("dual"),
    twilio_trim_silence: bool = Form(True),
    initial_silence_timeout_ms_phone: int = Form(5000),

    # Twilio (Renamed in UI, kept here for backend compatibility if needed, but mostly 'phone' suffixes covers it)
    # The 'phone' fields above map to Twilio.
    
    # Telnyx Specific
    stt_provider_telnyx: str = Form("azure"),
    stt_language_telnyx: str = Form("es-MX"),
    llm_provider_telnyx: str = Form("groq"),
    llm_model_telnyx: str = Form("llama-3.3-70b-versatile"),
    system_prompt_telnyx: str = Form(None),
    voice_name_telnyx: str = Form("es-MX-DaliaNeural"),
    voice_style_telnyx: str = Form(None),
    temperature_telnyx: float = Form(0.7),
    first_message_telnyx: str = Form("Hola, soy Andrea de Ubrokers. ¿Me escucha bien?"),
    first_message_mode_telnyx: str = Form("speak-first"),
    max_tokens_telnyx: int = Form(250),
    initial_silence_timeout_ms_telnyx: int = Form(5000),
    input_min_characters_telnyx: int = Form(4),
    enable_denoising_telnyx: bool = Form(True),
    voice_pacing_ms_telnyx: int = Form(500),
    silence_timeout_ms_telnyx: int = Form(1200),
    interruption_threshold_telnyx: int = Form(2),
    hallucination_blacklist_telnyx: str = Form("Pero.,Y...,Mm.,Oye.,Ah."),
    voice_speed_telnyx: float = Form(0.9),
    voice_sensitivity_telnyx: int = Form(3000),
    enable_krisp_telnyx: bool = Form(True),
    enable_vad_telnyx: bool = Form(True),
    
    # Telnyx Advanced
    idle_timeout_telnyx: float = Form(20.0),
    max_duration_telnyx: int = Form(600),
    idle_message_telnyx: str = Form("¿Hola? ¿Sigue ahí?"),
    enable_recording_telnyx: bool = Form(False),
    amd_config_telnyx: str = Form("disabled"),
    
    # 🔒 LOCKED: MODEL & CORE ARGS (DO NOT EDIT)
    # (Includes Voice Settings above)
    # Stage 1: Model & Voice
    first_message: str = Form("Hola, soy Andrea..."),
    first_message_mode: str = Form("speak-first"),
    max_tokens: int = Form(250),
    voice_id_manual: str = Form(None),
    background_sound_url: str = Form(None),
    input_min_characters: int = Form(3),
    
    # Stage 2: Transcriber
    silence_timeout_ms: int = Form(500),
    silence_timeout_ms_phone: int = Form(1200), # New
    segmentation_max_time: int = Form(30000),
    segmentation_strategy: str = Form("default"),
    enable_denoising: bool = Form(True), # Careful with boolean checkbox
    initial_silence_timeout_ms: int = Form(5000), # New
    punctuation_boundaries: str = Form(None), # New - FIXED
    
    # 🔒 LOCKED: TRANSCRIBING & FUNCTIONS (DO NOT EDIT)
    # Stage 2: Functions
    enable_end_call: bool = Form(True),
    enable_dial_keypad: bool = Form(False),
    transfer_phone_number: str = Form(None),

    stt_provider: str = Form(...),
    llm_provider: str = Form(...),
    tts_provider: str = Form(...),
    extraction_model: str = Form("llama-3.1-8b-instant")
):
    await db_service.update_agent_config(
        system_prompt=system_prompt,
        temperature=temperature,
        voice_speed=voice_speed,
        voice_speed_phone=voice_speed_phone,
        voice_name=voice_name,
        voice_style=voice_style, # FIXED: Was missing
        stt_language=stt_language,
        llm_model=llm_model,
        background_sound=background_sound,
        idle_timeout=idle_timeout,
        idle_message=idle_message,
        interruption_threshold=interruption_threshold,
        interruption_threshold_phone=interruption_threshold_phone,
        
        # New Audit Fields
        hallucination_blacklist=hallucination_blacklist,
        hallucination_blacklist_phone=hallucination_blacklist_phone,
        voice_pacing_ms=voice_pacing_ms,
        voice_pacing_ms_phone=voice_pacing_ms_phone,
        voice_name_phone=voice_name_phone,
        voice_style_phone=voice_style_phone,
        input_min_characters_phone=input_min_characters_phone,
        
        system_prompt_phone=system_prompt_phone,
        first_message_phone=first_message_phone,
        first_message_mode_phone=first_message_mode_phone,
        max_tokens_phone=max_tokens_phone,
        llm_provider_phone=llm_provider_phone,
        llm_model_phone=llm_model_phone,
        stt_provider_phone=stt_provider_phone,
        stt_language_phone=stt_language_phone,
        temperature_phone=temperature_phone,
        
        # Twilio
        enable_denoising_phone=enable_denoising_phone,
        twilio_machine_detection=twilio_machine_detection,
        twilio_record=twilio_record,
        twilio_recording_channels=twilio_recording_channels,
        twilio_trim_silence=twilio_trim_silence,
        initial_silence_timeout_ms_phone=initial_silence_timeout_ms_phone,
        
        # Telnyx
        stt_provider_telnyx=stt_provider_telnyx,
        stt_language_telnyx=stt_language_telnyx,
        llm_provider_telnyx=llm_provider_telnyx,
        llm_model_telnyx=llm_model_telnyx,
        system_prompt_telnyx=system_prompt_telnyx,
        voice_name_telnyx=voice_name_telnyx,
        voice_style_telnyx=voice_style_telnyx,
        temperature_telnyx=temperature_telnyx,
        first_message_telnyx=first_message_telnyx,
        first_message_mode_telnyx=first_message_mode_telnyx,
        max_tokens_telnyx=max_tokens_telnyx,
        initial_silence_timeout_ms_telnyx=initial_silence_timeout_ms_telnyx,
        input_min_characters_telnyx=input_min_characters_telnyx,
        enable_denoising_telnyx=enable_denoising_telnyx,
        voice_pacing_ms_telnyx=voice_pacing_ms_telnyx,
        silence_timeout_ms_telnyx=silence_timeout_ms_telnyx,
        interruption_threshold_telnyx=interruption_threshold_telnyx,
        hallucination_blacklist_telnyx=hallucination_blacklist_telnyx,
        voice_speed_telnyx=voice_speed_telnyx,
        voice_sensitivity_telnyx=voice_sensitivity_telnyx,
        enable_krisp_telnyx=enable_krisp_telnyx,
        enable_vad_telnyx=enable_vad_telnyx,
        enable_krisp_telnyx=enable_krisp_telnyx,
        enable_vad_telnyx=enable_vad_telnyx,
        
        idle_timeout_telnyx=idle_timeout_telnyx,
        max_duration_telnyx=max_duration_telnyx,
        idle_message_telnyx=idle_message_telnyx,
        enable_recording_telnyx=enable_recording_telnyx,
        amd_config_telnyx=amd_config_telnyx,

        max_duration=max_duration,
        # Stage 1
        first_message=first_message,
        first_message_mode=first_message_mode,
        max_tokens=max_tokens,
        voice_id_manual=voice_id_manual,
        background_sound_url=background_sound_url,
        input_min_characters=input_min_characters,
        
        # Stage 2
        silence_timeout_ms=silence_timeout_ms,
        silence_timeout_ms_phone=silence_timeout_ms_phone,
        segmentation_max_time=segmentation_max_time,
        segmentation_strategy=segmentation_strategy,
        enable_denoising=enable_denoising,
        initial_silence_timeout_ms=initial_silence_timeout_ms,
        punctuation_boundaries=punctuation_boundaries, # FIXED
        
        enable_end_call=enable_end_call,
        enable_dial_keypad=enable_dial_keypad,
        transfer_phone_number=transfer_phone_number,
        extraction_model=extraction_model, # NEW

        stt_provider=stt_provider,
        llm_provider=llm_provider,
        tts_provider=tts_provider
    )
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/api/config/patch")
async def patch_config(request: Request):
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
            "voice_pacing_ms_telnyx", "silence_timeout_ms_telnyx", "interruption_threshold_telnyx"
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

        await db_service.update_agent_config(**cleaned_data)
        return {"status": "success", "updated": cleaned_data}
    except Exception as e:
        logging.error(f"Config Patch Failed: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/dashboard/history-rows", response_class=HTMLResponse)
async def history_rows(request: Request, page: int = 1, limit: int = 20):
    try:
        offset = (page - 1) * limit
        history = await db_service.get_recent_calls(limit=limit, offset=offset)
        total = await db_service.get_total_calls()
        if total is None: total = 0
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        return templates.TemplateResponse("partials/history_panel.html", {
            "request": request,
            "history": history,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_items": total
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"<tr><td colspan='5' class='p-4 text-center text-red-400 font-bold'>Error cargando historial: {e}</td></tr>")

@router.post("/api/history/delete-selected")
async def delete_selected(request: Request):
    data = await request.json()
    call_ids = data.get("call_ids", [])
    if not call_ids:
        return {"status": "error", "message": "No IDs provided"}
    
    success = await db_service.delete_calls(call_ids)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete calls")

@router.get("/dashboard/call/{call_id}", response_class=HTMLResponse)
async def call_details(request: Request, call_id: int):
    call = await db_service.get_call_details(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return templates.TemplateResponse("call_details.html", {
        "request": request,
        "call": call
    })

@router.post("/api/history/clear")
async def clear_history():
    success = await db_service.clear_all_history()
    if not success:
         raise HTTPException(status_code=500, detail="Failed to clear history")
    return RedirectResponse(url="/dashboard", status_code=303)
