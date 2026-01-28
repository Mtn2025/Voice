"""
Prometheus Metrics Module

Exposes application and business metrics for monitoring.
"""
from prometheus_client import Counter, Gauge, Histogram, Info

# ============================================================================
# HTTP Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'path'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'path']
)

# ============================================================================
# Application Metrics
# ============================================================================

active_calls = Gauge(
    'voice_active_calls',
    'Number of active voice calls'
)

call_duration_seconds = Histogram(
    'voice_call_duration_seconds',
    'Voice call duration in seconds',
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

calls_total = Counter(
    'voice_calls_total',
    'Total voice calls',
    ['client_type', 'status']  # client_type: browser, twilio, telnyx
)

# ============================================================================
# AI Provider Metrics
# ============================================================================

stt_requests_total = Counter(
    'stt_requests_total',
    'Total STT (Speech-to-Text) requests',
    ['provider']
)

stt_latency_seconds = Histogram(
    'stt_latency_seconds',
    'STT response latency in seconds',
    ['provider'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM (Language Model) requests',
    ['provider', 'model']
)

llm_latency_seconds = Histogram(
    'llm_latency_seconds',
    'LLM response latency in seconds',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens consumed',
    ['provider', 'model', 'type']  # type: prompt, completion
)

tts_requests_total = Counter(
    'tts_requests_total',
    'Total TTS (Text-to-Speech) requests',
    ['provider']
)

tts_latency_seconds = Histogram(
    'tts_latency_seconds',
    'TTS response latency in seconds',
    ['provider'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# ============================================================================
# Error Metrics
# ============================================================================

errors_total = Counter(
    'errors_total',
    'Total errors by type',
    ['error_type', 'component']
)

# ============================================================================
# Database Metrics
# ============================================================================

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# ============================================================================
# Redis Metrics
# ============================================================================

redis_connected = Gauge(
    'redis_connected',
    'Redis connection status (1=connected, 0=disconnected)'
)

# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    'app',
    'Application information'
)

# Set app info on module load
app_info.info({
    'version': '1.0.0',
    'name': 'Asistente Andrea',
    'python_version': '3.12+'
})
