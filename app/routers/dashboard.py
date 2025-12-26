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
    languages = tts_provider.get_available_languages()
    
    # Models
    llm_provider = GroqProvider()
    models = await llm_provider.get_available_models()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "config": config,
        "voices": voices,
        "languages": languages,
        "models": models
    })

@router.post("/api/config/update")
async def update_config(
    system_prompt: str = Form(...),
    temperature: float = Form(...), # Restore temperature
    voice_speed: float = Form(...),
    voice_name: str = Form("es-MX-DaliaNeural"), 
    stt_language: str = Form("es-MX"), # New
    llm_model: str = Form("llama-3.3-70b-versatile"), # New
    background_sound: str = Form("none"), # New
    idle_timeout: float = Form(10.0), # New
    idle_message: str = Form("¿Hola? ¿Sigue ahí?"), # New
    max_duration: int = Form(600), # New

    
    # Stage 1: Model & Voice
    first_message: str = Form("Hola, soy Andrea..."),
    first_message_mode: str = Form("speak-first"),
    max_tokens: int = Form(250),
    voice_id_manual: str = Form(None),
    background_sound_url: str = Form(None),
    input_min_characters: int = Form(3),
    
    # Stage 2: Transcriber
    silence_timeout_ms: int = Form(500),
    segmentation_max_time: int = Form(30000),
    segmentation_strategy: str = Form("default"),
    enable_denoising: bool = Form(True), # Careful with boolean checkbox
    
    # Stage 2: Functions
    enable_end_call: bool = Form(True),
    enable_dial_keypad: bool = Form(False),
    transfer_phone_number: str = Form(None),

    stt_provider: str = Form(...),
    llm_provider: str = Form(...),
    tts_provider: str = Form(...)
):
    await db_service.update_agent_config(
        system_prompt=system_prompt,
        temperature=temperature,
        voice_speed=voice_speed,
        voice_name=voice_name,
        stt_language=stt_language,
        llm_model=llm_model,
        background_sound=background_sound,
        idle_timeout=idle_timeout,
        idle_message=idle_message,
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
        segmentation_max_time=segmentation_max_time,
        segmentation_strategy=segmentation_strategy,
        enable_denoising=enable_denoising,
        
        enable_end_call=enable_end_call,
        enable_dial_keypad=enable_dial_keypad,
        transfer_phone_number=transfer_phone_number,

        stt_provider=stt_provider,
        llm_provider=llm_provider,
        tts_provider=tts_provider
    )
    return RedirectResponse(url="/dashboard", status_code=303)
