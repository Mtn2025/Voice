"""
Unit tests for Performance Metrics - Module 5.

Validates MetricsCollector and latency tracking.
Tests metrics recording, global stats, trace management.
"""
import pytest
import asyncio
from app.observability import MetricsCollector, LatencyMetrics, get_metrics_collector


class TestMetricsCollector:
    """Test suite for metrics collection."""
    
    @pytest.mark.asyncio
    async def test_record_stt_latency(self):
        """Should record STT latency for a trace."""
        collector = MetricsCollector()
        trace_id = "test-trace-123"
        
        await collector.record_latency(trace_id, 'stt', 150.5)
        
        metrics = await collector.get_metrics(trace_id)
        assert metrics is not None
        assert metrics.stt_latency == 150.5
    
    @pytest.mark.asyncio
    async def test_record_llm_ttfb(self):
        """Should record LLM TTFB."""
        collector = MetricsCollector()
        trace_id = "test-trace-456"
        
        await collector.record_latency(trace_id, 'llm_ttfb', 350.0)
        
        metrics = await collector.get_metrics(trace_id)
        assert metrics.llm_ttfb == 350.0
    
    @pytest.mark.asyncio
    async def test_record_multiple_components(self):
        """Should record latencies for multiple components."""
        collector = MetricsCollector()
        trace_id = "test-trace-789"
        
        await collector.record_latency(trace_id, 'stt', 100.0)
        await collector.record_latency(trace_id, 'llm_total', 500.0)
        await collector.record_latency(trace_id, 'tts', 200.0)
        
        metrics = await collector.get_metrics(trace_id)
        assert metrics.stt_latency == 100.0
        assert metrics.llm_total == 500.0
        assert metrics.tts_latency == 200.0
        # Total should be calculated
        assert metrics.total_latency == 800.0
    
    @pytest.mark.asyncio
    async def test_global_stats_updated(self):
        """Global stats should update with running averages."""
        collector = MetricsCollector()
        
        await collector.record_latency("trace1", 'stt', 100.0)
        await collector.record_latency("trace2", 'stt', 200.0)
        
        stats = await collector.get_stats()
        assert stats['total_requests'] == 2
        assert stats['avg_stt_latency_ms'] == 150.0  # (100 + 200) / 2
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Should evict oldest traces when max_traces reached."""
        collector = MetricsCollector(max_traces=3)
        
        await collector.record_latency("trace1", 'stt', 100.0)
        await collector.record_latency("trace2", 'stt', 200.0)
        await collector.record_latency("trace3", 'stt', 300.0)
        
        # Adding 4th should evict oldest (trace1)
        await collector.record_latency("trace4", 'stt', 400.0)
        
        assert await collector.get_metrics("trace1") is None
        assert await collector.get_metrics("trace4") is not None
    
    @pytest.mark.asyncio
    async def test_get_all_metrics(self):
        """Should return all metrics."""
        collector = MetricsCollector()
        
        await collector.record_latency("trace1", 'stt', 100.0)
        await collector.record_latency("trace2", 'llm_ttfb', 200.0)
        
        all_metrics = await collector.get_all_metrics()
        assert len(all_metrics) == 2
    
    @pytest.mark.asyncio
    async def test_clear_trace(self):
        """Should clear metrics for specific trace."""
        collector = MetricsCollector()
        trace_id = "test-clear"
        
        await collector.record_latency(trace_id, 'stt', 100.0)
        assert await collector.get_metrics(trace_id) is not None
        
        await collector.clear_trace(trace_id)
        assert await collector.get_metrics(trace_id) is None
    
    def test_global_singleton(self):
        """get_metrics_collector should return same instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
    
    def test_latency_metrics_to_dict(self):
        """LatencyMetrics should export as dict."""
        metrics = LatencyMetrics(
            trace_id="test-123",
            stt_latency=100.5,
            llm_ttfb=250.3,
            tts_latency=150.7
        )
        
        data = metrics.to_dict()
        assert data['trace_id'] == "test-123"
        assert data['stt_latency_ms'] == 100.5
        assert data['llm_ttfb_ms'] == 250.3
        assert data['tts_latency_ms'] == 150.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
