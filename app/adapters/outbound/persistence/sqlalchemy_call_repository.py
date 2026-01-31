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
                call_id = await db_service.create_call(
                    session=session,
                    session_id=stream_id,
                    client_type=client_type
                )
                
                if not call_id:
                    raise ValueError("Failed to create call in DB")

                # Translate ORM model to domain CallRecord
                # Since db_service returns ID only, we construct the domain object with the ID we have
                return CallRecord(
                    id=call_id,
                    stream_id=stream_id,  # Use the original stream_id (which is session_id in DB)
                    client_type=client_type,
                    started_at=None, # Not returned by DB service create simple call
                    ended_at=None,
                    duration_seconds=None,
                    status="active"
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
