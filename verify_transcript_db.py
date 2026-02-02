
import asyncio
import logging
import uuid
from sqlalchemy import text
from app.api.routes_v2 import media_stream
from app.db.database import AsyncSessionLocal, engine
from app.db.models import Base
from app.core.orchestrator_v2 import VoiceOrchestratorV2
from app.adapters.outbound.persistence.sqlalchemy_call_repository import SQLAlchemyCallRepository
from app.adapters.outbound.persistence.sqlalchemy_transcript_repository import SQLAlchemyTranscriptRepository
from app.core.voice_ports import get_voice_ports

# Mock transport
from unittest.mock import AsyncMock

async def main():
    print("🚀 Initializing persistence test with SQLite...")
    
    # Force SQLite for test by overriding session factory or engine?
    # We set DATABASE_URL in env, so AsyncSessionLocal should use it.
    
    # 0. Initialize Schema (Create Tables in SQLite)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Schema Created (SQLite)")

    # 1. Seed Config (Required for Orchestrator)
    async with AsyncSessionLocal() as session:
        # Check if config exists
        result = await session.execute(text("SELECT count(*) FROM agent_configs"))
        count = result.scalar()
        if count == 0:
            print("🌱 Seeding default config...")
            await session.execute(text("INSERT INTO agent_configs (name, stt_provider, llm_provider, tts_provider) VALUES ('default', 'mock', 'mock', 'mock')"))
            await session.commit()
    
    try:
        # 2. Setup Dependencies
        ports = get_voice_ports(audio_mode="simulator")
        call_repo = SQLAlchemyCallRepository(AsyncSessionLocal)
        transcript_repo = SQLAlchemyTranscriptRepository(AsyncSessionLocal)
        
        # 3. Setup Orchestrator
        session_id = f"test_trans_{uuid.uuid4().hex[:8]}"
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
        
        # 4. Start Call
        await orch.start()
        # Orchestrator start is async and might have background tasks, but call creation is awaited in start()
        
        current_call_id = orch.call_db_id
        print(f"📞 Call Created: ID={current_call_id} (Session: {session_id})")
        
        if not current_call_id:
            print("❌ Failed to create call record! Check logs.")
            return

        # 5. Simulate Dialogue
        turns = [
            ("user", "Hola, buenas tardes"),
            ("assistant", "Hola, soy Andrea. ¿En qué puedo ayudarte?"),
            ("user", "Quiero agendar una cita"),
            ("assistant", "Claro, ¿para qué día?")
        ]
        
        print(f"🗣️ Simulating {len(turns)} turns...")
        for role, content in turns:
            await orch._handle_transcript(role, content)
            
        print("⏳ Waiting for persistence worker...")
        await asyncio.sleep(2) 
        
        # 6. Stop Call
        await orch.stop()
        
        # 7. VERIFY DB content
        async with AsyncSessionLocal() as session:
            print("\n🔎 Verifying Database Content:")
            result = await session.execute(text(
                "SELECT role, content FROM transcripts WHERE call_id = :cid ORDER BY id ASC"
            ), {"cid": current_call_id})
            
            rows = result.fetchall()
            
            print(f"📊 Found {len(rows)} transcripts for Call {current_call_id}")
            print("-" * 40)
            for row in rows:
                print(f"[{row.role.upper()}] {row.content}")
            print("-" * 40)
            
            if len(rows) == len(turns):
                print("✅ SUCCESS: All transcripts persisted correctly.")
            else:
                print(f"❌ FAILURE: Expected {len(turns)} rows, found {len(rows)}.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
