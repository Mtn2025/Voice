"""
Application Custom Exceptions - Punto B2

Defines the exception hierarchy for the Voice Orchestrator.
Using specific exceptions allows for better error handling, observability,
and meaningful API responses instead of generic 500 errors.
"""

class AppError(Exception):
    """Base exception for all application-specific errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class ConfigurationError(AppError):
    """Raised when there is a missing or invalid configuration."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="CONFIG_ERROR", details=details)

class ExternalServiceError(AppError):
    """Base for errors related to external APIs (Telnyx, Azure, Groq)."""
    def __init__(self, service: str, message: str, original_error: Exception | None = None):
        details = {"service": service}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(f"{service} Error: {message}", code="EXTERNAL_SERVICE_ERROR", details=details)

class TelnyxError(ExternalServiceError):
    """Specific to Telnyx API interactions."""
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__("Telnyx", message, original_error)

class AzureSpeechError(ExternalServiceError):
    """Specific to Azure Speech Services."""
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__("AzureSpeech", message, original_error)

class GroqError(ExternalServiceError):
    """Specific to Groq LLM API."""
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__("Groq", message, original_error)

class RedisError(AppError):
    """Errors related to Redis state management."""
    def __init__(self, message: str, original_error: Exception | None = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, code="REDIS_ERROR", details=details)

class WebhookError(AppError):
    """Validation or processing errors for incoming webhooks."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="WEBHOOK_ERROR", details=details)

class AudioProcessingError(AppError):
    """Errors during audio conversion, mixing, or buffering."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="AUDIO_ERROR", details=details)
