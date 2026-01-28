"""
OpenTelemetry Tracing Module

Distributed tracing for debugging and performance monitoring.
"""
import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_tracing(app, service_name: str = "asistente-andrea", otlp_endpoint: str | None = None):
    """
    Set up OpenTelemetry distributed tracing.

    Args:
        app: FastAPI application instance
        service_name: Name of the service for tracing
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")

    Note:
        If otlp_endpoint is None, tracing will be disabled.
        Set OTEL_EXPORTER_OTLP_ENDPOINT environment variable to enable.
    """
    if not otlp_endpoint:
        logger.info("OpenTelemetry tracing disabled (no OTLP endpoint configured)")
        return

    try:
        # Create resource with service name
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
        })

        # Set up tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True  # Use TLS in production
        )

        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        # Auto-instrument httpx (for external API calls)
        HTTPXClientInstrumentor().instrument()

        logger.info(f"✅ OpenTelemetry tracing enabled (endpoint: {otlp_endpoint})")

    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry tracing: {e}")


def get_tracer(name: str):
    """
    Get a tracer for manual instrumentation.

    Args:
        name: Name of the tracer (usually __name__)

    Returns:
        Tracer instance

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my_operation"):
            # Do work
            pass
    """
    return trace.get_tracer(name)
