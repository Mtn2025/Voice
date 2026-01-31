"""Exports de todos los puertos del dominio."""

from .audio_transport import AudioTransport
from .cache_port import CachePort
from .call_repository_port import CallRecord, CallRepositoryPort
from .config_repository_port import ConfigDTO, ConfigNotFoundException, ConfigRepositoryPort
from .llm_port import LLMException, LLMMessage, LLMPort, LLMRequest
from .stt_port import STTConfig, STTEvent, STTException, STTPort, STTRecognizer, STTResultReason
from .tts_port import TTSException, TTSPort, TTSRequest, VoiceMetadata

__all__ = [
    # Transport
    "AudioTransport",
    # Cache
    "CachePort",
    "ConfigDTO",
    "ConfigNotFoundException",
    # Config
    "ConfigRepositoryPort",
    "LLMException",
    "LLMMessage",
    # LLM
    "LLMPort",
    "LLMRequest",
    "STTConfig",
    "STTEvent",
    "STTException",
    # STT
    "STTPort",
    "STTRecognizer",
    "STTResultReason",
    "TTSException",
    # TTS
    "TTSPort",
    "TTSRequest",
    "VoiceMetadata",
]
