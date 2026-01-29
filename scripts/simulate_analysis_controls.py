import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Set SECURE dummy env vars to satisfy Pydantic
os.environ["POSTGRES_USER"] = "simulation_user"
os.environ["POSTGRES_PASSWORD"] = "secure_password_123"
os.environ["POSTGRES_DB"] = "simulation_db"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_HOST"] = "localhost"

sys.path.append(".")

from app.core.orchestrator import VoiceOrchestrator
from app.db.models import AgentConfig

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

async def run_simulation():
    print("\n📊 STARTING ANALYSIS SIMULATION (PHASE VII)\n==========================================")
    
    # -------------------------------------------------------------
    # SCENARIO 1: Analysis Setup Verification
    # -------------------------------------------------------------
    print("\n🧪 SCENARIO 1: Analysis Configuration Retrieval")
    
    # Custom Config
    config = AgentConfig(
        analysis_prompt="Summarize call in 3 bullet points.",
        success_rubric="Did client say yes?",
        extraction_schema={"intent": "string", "date": "date"},
        sentiment_analysis=True,
        log_webhook_url="https://logs.test.com"
    )
    
    # Initialize Orchestrator (Mock Transport)
    orch = VoiceOrchestrator(transport=AsyncMock(), client_type="twilio")
    orch.config = config # Inject config
    
    # Verify retrieval
    prompt = getattr(orch.config, "analysis_prompt", None)
    schema = getattr(orch.config, "extraction_schema", None)
    sentiment = getattr(orch.config, "sentiment_analysis", False)
    
    print(f"   -> Analysis Prompt: {prompt[:30]}...")
    print(f"   -> Extraction Schema: {schema}")
    print(f"   -> Sentiment Analysis: {sentiment}")
    
    if prompt == "Summarize call in 3 bullet points." and schema == {"intent": "string", "date": "date"} and sentiment is True:
        print("   ✅ PASSED: Analysis configuration retrieved correctly")
    else:
        print("   ❌ FAILED: Configuration mismatch")

    # -------------------------------------------------------------
    # SCENARIO 2: Webhook Traceability (Re-check)
    # -------------------------------------------------------------
    print("\n🧪 SCENARIO 2: Webhook Profile Separation")
    
    config_trace = AgentConfig()
    config_trace.webhook_url = "https://base.com"
    config_trace.webhook_url_phone = "https://phone.com"
    
    orch_phone = VoiceOrchestrator(transport=AsyncMock(), client_type="twilio")
    orch_phone.config = config_trace
    orch_phone._apply_profile_overlay()
    
    print(f"   -> Phone Webhook: {orch_phone.config.webhook_url}")
    
    if orch_phone.config.webhook_url == "https://phone.com":
         print("   ✅ PASSED: Phone webhook overlay correct")
    else:
         print(f"   ❌ FAILED: Expected https://phone.com, got {orch_phone.config.webhook_url}")

    print("\n🏁 ANALYSIS SIMULATION COMPLETED")

if __name__ == "__main__":
    asyncio.run(run_simulation())
