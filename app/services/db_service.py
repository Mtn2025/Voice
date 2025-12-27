from app.db.database import AsyncSessionLocal
from app.db.models import Call, Transcript, AgentConfig
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import desc
import logging

class DBService:
    async def create_call(self, session_id: str):
        async with AsyncSessionLocal() as session:
            try:
                # Check if exists first to avoid IntegrityError on reconnections
                result = await session.execute(select(Call).where(Call.session_id == session_id))
                existing_call = result.scalars().first()
                if existing_call:
                    return existing_call.id
                    
                call = Call(session_id=session_id)
                session.add(call)
                await session.commit()
                return call.id
            except Exception as e:
                logging.error(f"DB Error create_call: {e}")
                return None

    async def log_transcript(self, session_id: str, role: str, content: str, call_db_id: int = None):
        async with AsyncSessionLocal() as session:
            try:
                call_id = call_db_id
                if not call_id:
                     # Fallback: Find call by session_id
                    result = await session.execute(select(Call).where(Call.session_id == session_id))
                    call = result.scalars().first()
                    if call:
                        call_id = call.id
                
                if call_id:
                    transcript = Transcript(call_id=call_id, role=role, content=content)
                    session.add(transcript)
                    await session.commit()
            except Exception as e:
                logging.error(f"DB Error log_transcript: {e}")

    async def get_agent_config(self) -> AgentConfig:
        async with AsyncSessionLocal() as session:
            # Get default or first
            result = await session.execute(select(AgentConfig).where(AgentConfig.name == "default"))
            config = result.scalars().first()
            if not config:
                # Create default
                config = AgentConfig(name="default")
                session.add(config)
                await session.commit()
                await session.refresh(config)
            return config

    async def update_agent_config(self, **kwargs):
         async with AsyncSessionLocal() as session:
            result = await session.execute(select(AgentConfig).where(AgentConfig.name == "default"))
            config = result.scalars().first()
            if config:
                for key, value in kwargs.items():
                    setattr(config, key, value)
                await session.commit()
    async def get_recent_calls(self, limit: int = 20):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Call).order_by(Call.start_time.desc()).limit(limit))
            return result.scalars().all()

    async def get_call_details(self, call_id: int):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Call)
                .options(selectinload(Call.transcripts))
                .where(Call.id == call_id)
            )
            return result.scalars().first()

    async def update_call_extraction(self, call_id: int, extracted_data: dict):
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(Call).where(Call.id == call_id))
                call = result.scalars().first()
                if call:
                    call.extracted_data = extracted_data
                    await session.commit()
            except Exception as e:
                logging.error(f"DB Error update_call_extraction: {e}")


db_service = DBService()
