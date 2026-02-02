import logging
import asyncio
from collections.abc import Callable

from app.domain.ports.transcript_repository_port import TranscriptRepositoryPort
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

class SQLAlchemyTranscriptRepository(TranscriptRepositoryPort):
    """
    SQLAlchemy implementation of transcript repository.
    Includes a simple async queue to prevent blocking the main loop during high traffic.
    """

    def __init__(self, session_factory: Callable):
        self.session_factory = session_factory
        # Async Queue for non-blocking persistence
        self._queue = asyncio.Queue()
        self._worker_task = None

    async def start_worker(self):
        """Start the background persistence worker."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def save(self, call_id: int, role: str, content: str) -> None:
        """Enqueue transcript for saving."""
        if not call_id:
             logger.warning(f"⚠️ Cannot save transcript: No Call ID (role={role})")
             return
            
        # Ensure worker is running (lazy init)
        if self._worker_task is None:
            await self.start_worker()
            
        # Non-blocking enqueue
        try:
             self._queue.put_nowait((call_id, role, content))
        except Exception as e:
             logger.error(f"Failed to enqueue transcript: {e}")

    async def _worker_loop(self):
        """Background loop to process queue."""
        logger.info("📝 Transcript persistence worker started")
        while True:
            try:
                call_id, role, content = await self._queue.get()
                
                # Batch processing could go here, but kept simple as per request
                # Using existing db_service.log_transcript which creates its own session/context
                # But since we have session_factory, we should ideally use it directly to be cleaner.
                # However, db_service.log_transcript takes sesssion or handles it?
                # looking at db_service.py: log_transcript(session, ...)
                
                try:
                    async with self.session_factory() as session:
                        await db_service.log_transcript(
                            session=session,
                            session_id="ignore", # We have call_id
                            role=role, 
                            content=content,
                            call_db_id=call_id
                        )
                except Exception as e:
                    logger.error(f"❌ DB Error saving transcript: {e}")
                
                self._queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Transcript worker error: {e}")
                await asyncio.sleep(1) # Backoff
