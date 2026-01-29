"""Exports de adaptadores outbound."""

# TTS
from .tts.azure_tts_adapter import AzureTTSAdapter

# LLM
from .llm.groq_llm_adapter import GroqLLMAdapter

# STT
from .stt.azure_stt_adapter import AzureSTTAdapter

# Cache
from .cache.redis_cache_adapter import RedisCacheAdapter

# Persistence
from .persistence.postgres_config_repository import PostgresConfigRepository

__all__ = [
    "AzureTTSAdapter",
    "GroqLLMAdapter",
    "AzureSTTAdapter",
    "RedisCacheAdapter",
    "PostgresConfigRepository",
]
