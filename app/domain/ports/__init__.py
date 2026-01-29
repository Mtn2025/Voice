"""Exports de todos los puertos del dominio."""

from .tts_port import TTSPort, TTSRequest, VoiceMetadata, TTSException
from .llm_port import LLMPort, LLMMessage, LLMRequest, LLMException
from .stt_port import (
    STTPort,
    STTRecognizer,
    STTConfig,
    STTEvent,
    STTResultReason,
    STTException
)
from .config_repository_port import (
    ConfigRepositoryPort,
    ConfigDTO,
    ConfigNotFoundException
)
from .cache_port import CachePort
from .call_repository_port import CallRepositoryPort, CallRecord

__all__ = [
    # TTS
    "TTSPort",
    "TTSRequest",
    "VoiceMetadata",
    "TTSException",
    # LLM
    "LLMPort",
    "LLMMessage",
    "LLMRequest",
    "LLMException",
    # STT
    "STTPort",
    "STTRecognizer",
    "STTConfig",
    "STTEvent",
    "STTResultReason",
    "STTException",
    # Config
    "ConfigRepositoryPort",
    "ConfigDTO",
    "ConfigNotFoundException",
    # Cache
    "CachePort",
]
