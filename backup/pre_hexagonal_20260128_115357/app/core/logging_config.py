"""
Centralized Logging Configuration - Punto B1

Provides structured JSON logging with request tracing and PII sanitization.
Replaces basic text logging with production-ready structured logs.
"""

import logging
import sys
from typing import Any

from asgi_correlation_id import correlation_id
from pythonjsonlogger import jsonlogger

# Import sanitization logic from existing secure_logging
from app.core import secure_logging


class SecureJSONFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON Formatter that:
    1. Injects Trace ID (Correlation ID)
    2. Sanitizes sensitive data (PII/Secrets)
    3. Adds standard fields (timestamp, level, logger)
    """

    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]) -> None:
        """Add and sanitize fields in the log record."""
        super().add_fields(log_record, record, message_dict)

        # 1. Standard Fields
        if not log_record.get('timestamp'):
            # Use ISO 8601 format
            log_record['timestamp'] = record.asctime if hasattr(record, 'asctime') else self.formatTime(record)

        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

        log_record['logger'] = record.name

        # 2. Trace ID Injection (Correlation ID)
        # Check if correlation_id context var is set (from middleware)
        cid = correlation_id.get()
        if cid:
            log_record['trace_id'] = cid

        # 3. Sanitization (PII & Secrets)
        # Sanitize 'message' field
        if 'message' in log_record and isinstance(log_record['message'], str):
            log_record['message'] = secure_logging.sanitize_log_message(log_record['message'])

        # Sanitize all other fields recursively
        # We iterate over a copy of keys to modify dict safely
        for key, value in list(log_record.items()):
            # If value is string, sanitize it
            if isinstance(value, str):
                log_record[key] = secure_logging.sanitize_log_message(value)
            # If value is dict, sanitize keys and values
            elif isinstance(value, dict):
                log_record[key] = secure_logging.sanitize_dict(value)

            # Mask specific keys at root level if they slipped through
            # (sanitize_dict handles recursion, but let's be safe)
            key_lower = key.lower()
            if any(s in key_lower for s in secure_logging.SECRET_KEYS):
                log_record[key] = "***"


def configure_logging():
    """
    Configure global logging to use SecureJSONFormatter.
    Call this once at application startup.
    """
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    # Create Console Handler with JSON Formatter
    handler = logging.StreamHandler(sys.stdout)

    # Define format schema
    # message is the log message, timestamp/level/logger added by formatter
    formatter = SecureJSONFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(trace_id)s'
    )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set Level
    # Can be configured via env var in future
    root_logger.setLevel(logging.DEBUG)

    # Silence noisy libraries (Keep them quiet even in Debug mode to avoid flood)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # We will log requests ourselves or use generic
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log startup
    logger = logging.getLogger("app.core.logging_config")
    logger.info("✅ Structured JSON logging configured with Trace IDs")


# Helper to get logger (standard wrapper)
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
