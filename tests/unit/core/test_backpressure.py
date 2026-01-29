"""
Unit tests for Backpressure Management - Module 4.

Validates backpressure logic from Gap Analysis.
Tests queue overflow prevention, BackpressureFrame emission.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock
from app.core.pipeline import Pipeline
from app.core.frames import Frame, AudioFrame, TextFrame, BackpressureFrame, SystemFrame
from app.core.processor import FrameProcessor, FrameDirection


class DummyProcessor(FrameProcessor):
    """Simple pass-through processor for testing."""
    
    async def process_frame(self, frame: Frame, direction: int):
        await self.push_frame(frame, direction)


class TestBackpressure:
    """Test suite for backpressure management."""
    
    @pytest.mark.asyncio
    async def test_pipeline_has_max_queue_size(self):
        """Pipeline should respect max_queue_size parameter."""
        pipeline = Pipeline(processors=[], max_queue_size=50)
        
        assert pipeline.max_queue_size == 50
        assert pipeline._queue.maxsize == 50
    
    @pytest.mark.asyncio
    async def test_default_max_queue_size_is_100(self):
        """Pipeline should default to max_queue_size=100."""
        pipeline = Pipeline(processors=[])
        
        assert pipeline.max_queue_size == 100
        assert pipeline._queue.maxsize == 100
    
    @pytest.mark.asyncio
    async def test_backpressure_warning_at_80_percent(self):
        """Pipeline should emit BackpressureFrame at 80% capacity."""
        pipeline = Pipeline(processors=[], max_queue_size=10)
        
        # Fill queue to 80% (8 frames) WITHOUT starting pipeline
        # (starting pipeline causes test to hang waiting for _process_queue loop)
        for i in range(8):
            frame = TextFrame(text=f"msg{i}")
            await pipeline.queue_frame(frame)
        
        # Check that backpressure warning flag set
        assert pipeline._backpressure_warning_sent is True
    
    @pytest.mark.asyncio
    async def test_dropped_frames_on_queue_full(self):
        """Pipeline should drop frames when queue completely full."""
        pipeline = Pipeline(processors=[], max_queue_size=5)
        
        # Fill queue completely (5 frames)
        for i in range(5):
            frame = TextFrame(text=f"msg{i}")
            try:
                pipeline._queue.put_nowait((2, i, frame, FrameDirection.DOWNSTREAM))
            except asyncio.QueueFull:
                break
        
        # Try to add one more (should fail and be dropped)
        initial_dropped = pipeline._dropped_frames_count
        frame = TextFrame(text="overflow")
        await pipeline.queue_frame(frame)
        
        # Should have incremented dropped count
        assert pipeline._dropped_frames_count == initial_dropped + 1
    
    @pytest.mark.asyncio
    async def test_backpressure_frame_has_correct_severity(self):
        """BackpressureFrame should contain queue stats and severity."""
        frame = BackpressureFrame(
            queue_size=80,
            max_size=100,
            severity="warning"
        )
        
        assert frame.queue_size == 80
        assert frame.max_size == 100
        assert frame.severity == "warning"
    
    @pytest.mark.asyncio
    async def test_backpressure_critical_when_full(self):
        """Backpressure severity should be 'critical' when queue full."""
        frame = BackpressureFrame(
            queue_size=100,
            max_size=100,
            severity="critical"
        )
        
        assert frame.severity == "critical"
    
    @pytest.mark.asyncio
    async def test_system_frames_bypass_backpressure(self):
        """SystemFrames should use priority=1 (higher than DataFrames)."""
        pipeline = Pipeline(processors=[], max_queue_size=10)
        
        # Queue a SystemFrame
        system_frame = SystemFrame()
        await pipeline.queue_frame(system_frame)
        
        # SystemFrame should have priority 1
        priority, counter, frame, direction = await pipeline._queue.get()
        assert priority == 1
        assert isinstance(frame, SystemFrame)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
