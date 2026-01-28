import logging
import traceback

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import AgentConfig, Call
from app.db.models import Transcript as TranscriptModel


class DBService:
    async def create_call(self, session: AsyncSession, session_id: str, client_type: str = "simulator") -> int | None:
        try:
            # Check if exists first to avoid IntegrityError on reconnections
            result = await session.execute(select(Call).where(Call.session_id == session_id))
            existing_call = result.scalars().first()
            if existing_call:
                return existing_call.id

            call = Call(session_id=session_id, client_type=client_type)
            session.add(call)
            await session.commit()
            return call.id
        except Exception as e:
            logging.error(f"❌ DB Error create_call: {e}")
            logging.error(traceback.format_exc())
            return None

    async def log_transcript(
        self,
        session: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        call_db_id: int | None = None
    ) -> None:
        try:
            call_id = call_db_id
            if not call_id:
                     # Fallback: Find call by session_id
                result = await session.execute(select(Call).where(Call.session_id == session_id))
                call = result.scalars().first()
                if call:
                    call_id = call.id

            if call_id:
                transcript = TranscriptModel(call_id=call_id, role=role, content=content)
                session.add(transcript)
                await session.commit()
        except Exception as e:
            logging.error(f"DB Error log_transcript: {e}")

    async def get_agent_config(self, session: AsyncSession) -> AgentConfig:
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

    async def update_agent_config(self, session: AsyncSession, **kwargs):
        result = await session.execute(select(AgentConfig).where(AgentConfig.name == "default"))
        config = result.scalars().first()
        if config:
            for key, value in kwargs.items():
                setattr(config, key, value)
            await session.commit()

    async def end_call(self, session: AsyncSession, call_id: int):
        try:
            result = await session.execute(select(Call).where(Call.id == call_id))
            call = result.scalars().first()
            if call:
                import datetime
                call.end_time = datetime.datetime.utcnow()
                call.status = "completed"
                await session.commit()
                logging.info(f"✅ Call {call_id} marked as completed.")
        except Exception as e:
            logging.error(f"❌ DB Error end_call: {e}")

    async def get_recent_calls(self, session: AsyncSession, limit: int = 20, offset: int = 0):
        result = await session.execute(
            select(Call)
            .order_by(Call.start_time.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_total_calls(self, session: AsyncSession):
             # Count query
             result = await session.execute(select(func.count(Call.id)))
             return result.scalar()

    async def delete_calls(self, session: AsyncSession, call_ids: list[int]):
        try:
            # Delete Transcripts first
            await session.execute(delete(TranscriptModel).where(TranscriptModel.call_id.in_(call_ids)))
            # Delete Calls
            await session.execute(delete(Call).where(Call.id.in_(call_ids)))
            await session.commit()
            return True
        except Exception as e:
            logging.error(f"DB Error delete_calls: {e}")
            await session.rollback()
            return False

    async def get_call_details(self, session: AsyncSession, call_id: int):
        result = await session.execute(
            select(Call)
            .options(selectinload(Call.transcripts))
            .where(Call.id == call_id)
        )
        return result.scalars().first()

    async def update_call_extraction(self, session: AsyncSession, call_id: int, extracted_data: dict):
        try:
            result = await session.execute(select(Call).where(Call.id == call_id))
            call = result.scalars().first()
            if call:
                call.extracted_data = extracted_data
                await session.commit()
        except Exception as e:
            logging.error(f"DB Error update_call_extraction: {e}")

    async def clear_all_history(self, session: AsyncSession):
        try:
            # Delete Transcripts first (FK dependency)
            await session.execute(delete(TranscriptModel))
            # Delete Calls
            await session.execute(delete(Call))
            await session.commit()
            return True
        except Exception as e:
            logging.error(f"DB Error clear_all_history: {e}")
            await session.rollback()
            return False


db_service = DBService()
