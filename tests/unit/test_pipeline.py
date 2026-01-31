import pytest
import asyncio
from app.core.frames import Frame, TextFrame, CancelFrame
from app.core.processor import FrameProcessor, FrameDirection
from app.core.pipeline import Pipeline

class MockProcessor(FrameProcessor):
    def __init__(self, name="Mock"):
        super().__init__(name=name)
        self.processed = []

    async def process_frame(self, frame: Frame, direction: int):
        self.processed.append((frame, direction))
        await self.push_frame(frame, direction)

@pytest.mark.asyncio
async def test_frame_flow():
    """Verify frames flow downstream through processors."""
    p1 = MockProcessor("P1")
    p2 = MockProcessor("P2")
    
    pipeline = Pipeline([p1, p2])
    await pipeline.start()
    
    frame = TextFrame(text="Hello")
    await pipeline.queue_frame(frame, direction=FrameDirection.DOWNSTREAM)
    
    # Wait a bit for async processing
    await asyncio.sleep(0.1)
    await pipeline.stop()
    
    assert len(p1.processed) == 1
    assert len(p2.processed) == 1
    assert p1.processed[0][0] == frame
    assert p2.processed[0][0] == frame

@pytest.mark.asyncio
async def test_interruption_handling():
    """Verify CancelFrame flows and can be handled."""
    p1 = MockProcessor("P1")
    
    pipeline = Pipeline([p1])
    await pipeline.start()
    
    # Send Cancel Frame
    cancel = CancelFrame(reason="User Interrupt")
    await pipeline.queue_frame(cancel)
    
    await asyncio.sleep(0.1)
    await pipeline.stop()
    
    assert len(p1.processed) == 1
    assert isinstance(p1.processed[0][0], CancelFrame)

@pytest.mark.asyncio
async def test_processor_linking():
    """Verify processors are linked correctly."""
    p1 = MockProcessor("P1")
    p2 = MockProcessor("P2")
    _pipeline = Pipeline([p1, p2])
    
    # Internal linking check (implementation detail)
    # Pipeline adds Source and Sink, so: Source -> P1 -> P2 -> Sink
    assert p1._next == p2
    assert p2._prev == p1
    assert p2._next.name == "PipelineSink"
    assert p1._prev.name == "PipelineSource"
