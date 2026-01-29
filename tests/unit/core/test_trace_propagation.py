"""
Unit tests for Trace ID Propagation - Module 3.

Validates distributed tracing implementation from Gap Analysis.
Tests trace_id propagation across frames, TTFB logging.
"""
import pytest
from app.core.frames import Frame, AudioFrame, TextFrame


class TestTracePropagation:
    """Test suite for trace ID propagation."""
    
    def test_frame_generates_trace_id_automatically(self):
        """Frame should auto-generate trace_id if not provided."""
        frame = AudioFrame(data=b"test", sample_rate=8000)
        
        assert frame.trace_id != ""
        assert len(frame.trace_id) == 36  # UUID length
    
    def test_frame_generates_span_id_automatically(self):
        """Frame should always generate unique span_id."""
        frame = AudioFrame(data=b"test", sample_rate=8000)
        
        assert frame.span_id != ""
        assert len(frame.span_id) == 36  # UUID length
    
    def test_trace_id_propagates_across_frames(self):
        """trace_id should propagate from one frame to another."""
        trace_id = "test-trace-123"
        
        frame1 = AudioFrame(data=b"test", sample_rate=8000, trace_id=trace_id)
        frame2 = TextFrame(text="hello", trace_id=frame1.trace_id)
        
        assert frame1.trace_id == trace_id
        assert frame2.trace_id == trace_id
        assert frame1.span_id != frame2.span_id  # Different spans
    
    def test_different_frames_different_span_ids(self):
        """Each frame should have unique span_id even with same trace_id."""
        trace_id = "shared-trace"
        
        frame1 = AudioFrame(data=b"1", sample_rate=8000, trace_id=trace_id)
        frame2 = AudioFrame(data=b"2", sample_rate=8000, trace_id=trace_id)
        
        assert frame1.trace_id == frame2.trace_id
        assert frame1.span_id != frame2.span_id
    
    def test_frame_metadata_accessible(self):
        """Frame metadata should be accessible for trace context."""
        frame = TextFrame(
            text="test",
            trace_id="trace-123",
            metadata={'user': 'john', 'session': 'abc'}
        )
        
        assert frame.trace_id == "trace-123"
        assert frame.metadata['user'] == 'john'
        assert frame.metadata['session'] == 'abc'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
