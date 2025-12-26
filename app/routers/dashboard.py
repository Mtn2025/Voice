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
    models = llm_provider.get_available_models()
    
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
    llm_model: str = Form("deepseek-r1-distill-llama-70b"), # New
    background_sound: str = Form("none"), # New
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
        stt_provider=stt_provider,
        llm_provider=llm_provider,
        tts_provider=tts_provider
    )
    return RedirectResponse(url="/dashboard", status_code=303)
