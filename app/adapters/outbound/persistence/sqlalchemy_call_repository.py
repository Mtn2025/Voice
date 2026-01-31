"""
SQLAlchemy implementation of CallRepositoryPort.

Adapter that translates domain calls to SQLAlchemy operations.
"""

import logging
from collections.abc import Callable

from app.domain.ports.call_repository_port import CallRecord, CallRepositoryPort
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class SQLAlchemyCallRepository(CallRepositoryPort):
    """
    SQLAlchemy adapter for CallRepositoryPort.

    ✅ HEXAGONAL: Infrastructure adapter implementing domain port
    ✅ Encapsulates all SQLAlchemy/AsyncSessionLocal logic
    """

    def __init__(self, session_factory: Callable):
        """
        Args:
            session_factory: Factory function to create async sessions
                           (e.g., AsyncSessionLocal)
        """
        self.session_factory = session_factory

    async def create_call(
        self,
        stream_id: str,
        client_type: str,
        metadata: dict
    ) -> CallRecord:
        """Create new call record in database."""
        try:
            async with self.session_factory() as session:
                call_record = await db_service.create_call(
                    session=session,
                    stream_id=stream_id,
                    client_type=client_type,
                    metadata=metadata
                )

                # Translate ORM model to domain CallRecord
                return CallRecord(
                    id=call_record.id,
                    stream_id=call_record.stream_id,
                    client_type=call_record.client_type,
                    started_at=call_record.started_at,
                    ended_at=call_record.ended_at,
                    duration_seconds=call_record.duration_seconds,
                    status=call_record.status or "active"
                )

        except Exception as e:
            logger.error(f"Failed to create call record: {e}")
            raise

    async def end_call(self, call_id: int) -> None:
        """Finalize call record."""
        try:
            async with self.session_factory() as session:
                await db_service.end_call(session, call_id)
                logger.info(f"Call {call_id} ended successfully")

        except Exception as e:
            logger.error(f"Failed to end call {call_id}: {e}")
            # ✅ RESILIENCE: Non-blocking - log but don't crash orchestrator

    async def get_call(self, call_id: int) -> CallRecord | None:
        """Get call record by ID."""
        try:
            async with self.session_factory() as session:
                call = await db_service.get_call(session, call_id)

                if not call:
                    return None

                return CallRecord(
                    id=call.id,
                    stream_id=call.stream_id,
                    client_type=call.client_type,
                    started_at=call.started_at,
                    ended_at=call.ended_at,
                    duration_seconds=call.duration_seconds,
                    status=call.status or "active"
                )

        except Exception as e:
            logger.warning(f"Failed to get call {call_id}: {e}")
            return None
