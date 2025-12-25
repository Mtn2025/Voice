from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import routes
from app.routers import dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load resources
    print("Starting Voice Orchestrator...")
    
    # Init DB Tables
    from app.db.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    # Clean up resources
    print("Shutting down Voice Orchestrator...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.include_router(routes.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router)


@app.get("/")
async def root():
    return {"message": "Voice Orchestrator is running"}
