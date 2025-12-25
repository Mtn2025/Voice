from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.db_service import db_service
from app.db.models import AgentConfig
import logging

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = await db_service.get_agent_config()
    return templates.TemplateResponse("dashboard.html", {"request": request, "config": config})

@router.post("/api/config/update")
async def update_config(
    system_prompt: str = Form(...),
    temperature: float = Form(...),
    voice_speed: float = Form(...),
    stt_provider: str = Form(...),
    llm_provider: str = Form(...),
    tts_provider: str = Form(...)
):
    await db_service.update_agent_config(
        system_prompt=system_prompt,
        temperature=temperature,
        voice_speed=voice_speed,
        stt_provider=stt_provider,
        llm_provider=llm_provider,
        tts_provider=tts_provider
    )
    return RedirectResponse(url="/dashboard", status_code=303)
