import pytest
from unittest.mock import AsyncMock, MagicMock
from app.adapters.outbound.persistence.sqlalchemy_transcript_repository import SQLAlchemyTranscriptRepository

@pytest.mark.asyncio
async def test_transcript_persistence_queue():
    # 1. Setup
    mock_session_factory = MagicMock()
    repo = SQLAlchemyTranscriptRepository(mock_session_factory)
    
    # Mock Worker Logic (Partial Integration)
    # Since we can't easily wait for the background worker in a unit test without complex synchronization,
    # we will test the Queue mechanism and validation.
    
    call_id = 123
    
    # 2. Test Enqueue
    await repo.save(call_id, "user", "Hello")
    await repo.save(call_id, "assistant", "Hi there")
    await repo.save(call_id, "user", "Bye")

    assert repo._queue.qsize() == 3
    
    # 3. Verify Worker Processing (Manually consume queue to verify data)
    item1 = await repo._queue.get()
    assert item1 == (123, "user", "Hello")
    
    item2 = await repo._queue.get()
    assert item2 == (123, "assistant", "Hi there")
    
    item3 = await repo._queue.get()
    assert item3 == (123, "user", "Bye")

@pytest.mark.asyncio
async def test_transcript_persistence_missing_id():
    repo = SQLAlchemyTranscriptRepository(MagicMock())
    
    # Should log warning and not enqueue
    await repo.save(None, "user", "Test")
    assert repo._queue.qsize() == 0
