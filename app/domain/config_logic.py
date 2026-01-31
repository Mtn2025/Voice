"""
Domain logic for configuration management.
Encapsulates business rules for applying client-specific overrides.
"""
import logging

logger = logging.getLogger(__name__)

def apply_client_overlay(config, client_type: str):
    """
    Apply client-specific configuration overlays to the config object.
    Modifies the config object in-place (in memory).

    Args:
        config: AgentConfig model instance (ORM or Pydantic)
        client_type: "browser", "twilio", or "telnyx"
    """
    if client_type == "browser":
        # Browser optimizations
        # WebSockets allows near-instant latency, so we remove artificial pacing
        try:
            config.voice_pacing_ms = 0
            config.silence_timeout_ms = 1200  # Slightly more permissive for browser mic
            logger.debug("[Config] Applied Browser overlay: pacing=0, silence=1200")
        except AttributeError:
            pass

    elif client_type in ("twilio", "telnyx"):
        # Telephony defaults
        # We need careful pacing to avoid "talking over" feeling on phone lines
        pacing_mode = getattr(config, 'conversation_pacing_mode', 'normal')

        try:
            if pacing_mode == 'fast':
                config.voice_pacing_ms = 200
                config.silence_timeout_ms = 800
            elif pacing_mode == 'normal':
                config.voice_pacing_ms = 400
                config.silence_timeout_ms = 1000
            elif pacing_mode == 'relaxed':
                config.voice_pacing_ms = 600
                config.silence_timeout_ms = 1500

            logger.debug(f"[Config] Applied Phone overlay ({pacing_mode}): pacing={config.voice_pacing_ms}")
        except AttributeError:
            pass
