"""
Performance Metrics Collection - Module 5.

Centralized metrics collector for latency tracking across all adapters.
Resolves Gap Analysis #9 (TTFB metrics), #10 (queue depth monitoring).
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Latency breakdown by component for a conversational turn."""
    trace_id: str

    # Component latencies (milliseconds)
    stt_latency: float = 0.0
    llm_ttfb: float = 0.0        # Time To First Byte from LLM
    llm_total: float = 0.0       # Total LLM generation time
    tts_latency: float = 0.0

    # Pipeline metrics
    total_latency: float = 0.0
    queue_depth_max: int = 0

    # Timestamps
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Export metrics as dict."""
        return {
            'trace_id': self.trace_id,
            'stt_latency_ms': round(self.stt_latency, 2),
            'llm_ttfb_ms': round(self.llm_ttfb, 2),
            'llm_total_ms': round(self.llm_total, 2),
            'tts_latency_ms': round(self.tts_latency, 2),
            'total_latency_ms': round(self.total_latency, 2),
            'queue_depth_max': self.queue_depth_max,
            'created_at': self.created_at
        }


class MetricsCollector:
    """
    ✅ Module 5: Centralized performance metrics collector.

    Thread-safe metrics collection for distributed tracing.
    Stores metrics by trace_id for post-analysis.
    """

    def __init__(self, max_traces: int = 1000):
        """
        Initialize metrics collector.

        Args:
            max_traces: Maximum number of traces to keep in memory (LRU)
        """
        self._metrics: dict[str, LatencyMetrics] = {}
        self._max_traces = max_traces
        self._lock = asyncio.Lock()

        # Global stats
        self._stats = {
            'total_requests': 0,
            'avg_stt_latency': 0.0,
            'avg_llm_ttfb': 0.0,
            'avg_tts_latency': 0.0,
        }

    async def record_latency(
        self,
        trace_id: str,
        component: str,
        latency_ms: float
    ):
        """
        Record component latency for a trace.

        Args:
            trace_id: Conversation turn ID
            component: 'stt', 'llm_ttfb', 'llm_total', 'tts'
            latency_ms: Latency in milliseconds
        """
        async with self._lock:
            # Get or create metrics for this trace
            if trace_id not in self._metrics:
                # LRU eviction if needed
                if len(self._metrics) >= self._max_traces:
                    # Remove oldest trace (simple FIFO)
                    oldest = min(self._metrics.values(), key=lambda m: m.created_at)
                    del self._metrics[oldest.trace_id]

                self._metrics[trace_id] = LatencyMetrics(trace_id=trace_id)

            metrics = self._metrics[trace_id]

            # Update component latency
            if component == 'stt':
                metrics.stt_latency = latency_ms
            elif component == 'llm_ttfb':
                metrics.llm_ttfb = latency_ms
            elif component == 'llm_total':
                metrics.llm_total = latency_ms
            elif component == 'tts':
                metrics.tts_latency = latency_ms
            elif component == 'queue_depth':
                metrics.queue_depth_max = max(metrics.queue_depth_max, int(latency_ms))

            # Recalculate total (if all components available)
            if all([metrics.stt_latency, metrics.llm_total, metrics.tts_latency]):
                metrics.total_latency = (
                    metrics.stt_latency +
                    metrics.llm_total +
                    metrics.tts_latency
                )

            # Update global stats
            self._update_stats(component, latency_ms)

    def _update_stats(self, component: str, latency_ms: float):
        """Update running average stats."""
        self._stats['total_requests'] += 1
        n = self._stats['total_requests']

        # Running average
        if component == 'stt':
            prev = self._stats['avg_stt_latency']
            self._stats['avg_stt_latency'] = prev + (latency_ms - prev) / n
        elif component == 'llm_ttfb':
            prev = self._stats['avg_llm_ttfb']
            self._stats['avg_llm_ttfb'] = prev + (latency_ms - prev) / n
        elif component == 'tts':
            prev = self._stats['avg_tts_latency']
            self._stats['avg_tts_latency'] = prev + (latency_ms - prev) / n

    async def get_metrics(self, trace_id: str) -> LatencyMetrics | None:
        """Get metrics for a specific trace."""
        async with self._lock:
            return self._metrics.get(trace_id)

    async def get_all_metrics(self) -> list[LatencyMetrics]:
        """Get all metrics (for export/analysis)."""
        async with self._lock:
            return list(self._metrics.values())

    async def get_stats(self) -> dict:
        """Get global statistics."""
        async with self._lock:
            return {
                'total_requests': self._stats['total_requests'],
                'avg_stt_latency_ms': round(self._stats['avg_stt_latency'], 2),
                'avg_llm_ttfb_ms': round(self._stats['avg_llm_ttfb'], 2),
                'avg_tts_latency_ms': round(self._stats['avg_tts_latency'], 2),
                'traces_in_memory': len(self._metrics)
            }

    async def clear_trace(self, trace_id: str):
        """Remove metrics for a specific trace."""
        async with self._lock:
            self._metrics.pop(trace_id, None)


# Global singleton instance
_global_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _global_collector  # noqa: PLW0603 - Observability singleton pattern
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
