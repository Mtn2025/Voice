from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import routes
from app.routers import dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load resources
    print("Starting Voice Orchestrator...")
    
    # Init DB Tables
    from app.db.database import engine
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Auto-Migration for stt_language (Lightweight)
        from sqlalchemy import text
        try:
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS stt_language VARCHAR DEFAULT 'es-MX'"))
            # Also ensure llm_model col exists too if we wanted, but voice_name exists by default? 
            # Check models.py again. voice_name exists. llm_model doesn't.
            # Let's add llm_model too while we are at it to fulfill previous promise.
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS llm_model VARCHAR DEFAULT 'deepseek-r1-distill-llama-70b'"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS background_sound VARCHAR DEFAULT 'none'"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS idle_timeout FLOAT DEFAULT 10.0"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS idle_message VARCHAR DEFAULT '¿Hola? ¿Sigue ahí?'"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS max_duration INTEGER DEFAULT 600"))
            
            # VAPI Parity Stage 1
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS voice_style VARCHAR"))
            
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS first_message VARCHAR DEFAULT 'Hola, soy Andrea de Ubrokers. ¿Me escucha bien?'"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS first_message_mode VARCHAR DEFAULT 'speak-first'"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS max_tokens INTEGER DEFAULT 250"))
            
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS voice_id_manual VARCHAR"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS background_sound_url VARCHAR"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS input_min_characters INTEGER DEFAULT 3"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS punctuation_boundaries VARCHAR"))
            
            # VAPI Parity Stage 2
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS silence_timeout_ms INTEGER DEFAULT 500"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS segmentation_max_time INTEGER DEFAULT 30000"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS segmentation_strategy VARCHAR DEFAULT 'default'"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS enable_denoising BOOLEAN DEFAULT TRUE"))
            
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS enable_end_call BOOLEAN DEFAULT TRUE"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS enable_dial_keypad BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS transfer_phone_number VARCHAR"))
            
            # Data Extraction
            await conn.execute(text("ALTER TABLE calls ADD COLUMN IF NOT EXISTS extracted_data JSONB"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS extraction_model VARCHAR DEFAULT 'llama-3.1-8b-instant'"))
            await conn.execute(text("ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS interruption_threshold INTEGER DEFAULT 5"))

        except Exception as e:
            print(f"Migration warning: {e}")
        
    yield
    # Clean up resources
    print("Shutting down Voice Orchestrator...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(routes.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router)


from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")
