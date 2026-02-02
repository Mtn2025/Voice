
import asyncio
import logging
import uuid
import json
import os
from unittest.mock import AsyncMock, patch

from sqlalchemy import text
from app.db.database import engine, AsyncSessionLocal
from app.db.models import Base
from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.adapters.outbound.persistence.sqlalchemy_call_repository import SQLAlchemyCallRepository
from app.adapters.outbound.persistence.sqlalchemy_transcript_repository import SQLAlchemyTranscriptRepository
from app.core.voice_ports import get_voice_ports
from app.core.config import settings

# Setup Logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("ValidationVIII")
logger.setLevel(logging.INFO)

async def load_env_manual():
    """Load .env manually for the test script context"""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key] = val
                    # Also update settings singleton if possible, or assume it reads env
    except Exception:
        pass

async def main():
    print("🚀 Starting Phase VIII Validation (Extraction & Transcripts)...")
    await load_env_manual()

    # 1. Initialize Test DB (SQLite)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed Config
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT count(*) FROM agent_configs"))
        if result.scalar() == 0:
            await session.execute(text("INSERT INTO agent_configs (name, stt_provider, llm_provider, tts_provider) VALUES ('default', 'mock', 'mock', 'mock')"))
            await session.commit()

    # 2. Setup Components
    ports = get_voice_ports(audio_mode="simulator")
    # For testing, we ensure we use our SQLite session factory
    call_repo = SQLAlchemyCallRepository(AsyncSessionLocal)
    transcript_repo = SQLAlchemyTranscriptRepository(AsyncSessionLocal)
    
    # 3. Simulate Orchestrator
    session_id = f"validation_{uuid.uuid4().hex[:8]}"
    orch = VoiceOrchestratorV2(
        transport=AsyncMock(),
        stt_port=ports.stt,
        llm_port=ports.llm,
        tts_port=ports.tts,
        config_repo=ports.config_repo,
        call_repo=call_repo,
        transcript_repo=transcript_repo,
        client_type="simulator",
        initial_context=None
    )
    orch.stream_id = session_id
    
    # Start Call
    await orch.start()
    current_call_id = orch.call_db_id
    print(f"📞 Active Call ID: {current_call_id}")

    # 4. Simulate Specific Dialogue (The 'Carlos' Scenario)
    dialogue = [
        ("assistant", "Hola, soy Andrea de Ubrokers. ¿En qué puedo ayudarle?"),
        ("user", "Me llamo Carlos, mi teléfono es 5511223344, sí quiero una cita para el martes"),
        ("assistant", "Perfecto Carlos, agendo tu cita para el martes. ¿Algo más?"),
        ("user", "Eso es todo, gracias."),
        ("assistant", "Hasta luego.")
    ]
    
    print("\n🗣️ Simulating Dialogue...")
    for role, content in dialogue:
        print(f"   [{role.upper()}]: {content}")
        await orch._handle_transcript(role, content)
    
    print("\n⏳ Processing Post-Call Actions...")
    
    # MOCK the actual LLM extraction to ensure we validate PERSISTENCE (reliable test)
    # We want to prove that IF extraction returns data, it gets saved.
    # Testing the LLM prompt itself is flaky in CI contexts without live keys.
    expected_extraction = {
      "summary": "El usuario Carlos (5511223344) aceptó agendar una cita para el martes",
      "intent": "appointment_scheduling",
      "sentiment": "positive",
      "extracted_entities": {
        "name": "Carlos",
        "phone": "5511223344",
        "email": None,
        "appointment_date": "2026-02-10T10:00:00"
      },
      "next_action": "follow_up"
    }

    with patch("app.services.extraction_service.extraction_service.extract_post_call", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = expected_extraction
        
        # Stop call (Triggers extraction logic)
        await orch.stop()
    
    # Wait for async queue
    await asyncio.sleep(2)

    # 5. Verify Database
    print("\n🔎 database Verification Results:")
    async with AsyncSessionLocal() as session:
        # TEST 1: Extraction
        res_call = await session.execute(text("SELECT extracted_data FROM calls WHERE id = :id"), {"id": current_call_id})
        row_call = res_call.first()
        
        print(f"\n🔹 TEST 1: Post-Call Extraction")
        if row_call and row_call.extracted_data:
             data = row_call.extracted_data
             if isinstance(data, str):
                 data = json.loads(data)
             
             # Basic assertions
             if data.get("intent") == "appointment_scheduling" and data["extracted_entities"]["name"] == "Carlos":
                 print("✅ PASSED: Extracted Data persisted correctly.")
                 print(f"   JSON: {json.dumps(data, indent=2)}")
             else:
                 print("❌ FAILED: Data content mismatch.")
                 print(f"   Got: {data}")
        else:
             print("❌ FAILED: extracted_data is NULL or Empty.")

        # TEST 2: Transcripts
        res_trans = await session.execute(text("SELECT role, content FROM transcripts WHERE call_id = :id ORDER BY id"), {"id": current_call_id})
        rows_trans = res_trans.fetchall()
        
        print(f"\n🔹 TEST 2: Transcript Persistence")
        print(f"   Count: {len(rows_trans)} / {len(dialogue)}")
        
        match = True
        if len(rows_trans) != len(dialogue):
            match = False
        else:
            for i, row in enumerate(rows_trans):
                if row.role != dialogue[i][0] or row.content != dialogue[i][1]:
                    match = False
                    break
        
        if match:
            print("✅ PASSED: All transcripts saved exactly as simulated.")
        else:
            print("❌ FAILED: Transcript mismatch.")
            for row in rows_trans:
                print(f"   DB: {row.role} - {row.content}")

if __name__ == "__main__":
    asyncio.run(main())
