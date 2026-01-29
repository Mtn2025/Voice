"""
Provider Configuration Objects - Pure Domain Models.

Clean configuration objects for adapters (hexagonal architecture).
Adapters receive config objects from factory, not raw settings.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class STTProviderConfig:
    """Configuration for STT providers (technology-agnostic)."""
    provider: str  # "azure", "google", "deepgram"
    api_key: str
    region: Optional[str] = None
    language: str = "es-MX"
    sample_rate: int = 8000
    
    # Provider-specific options (extensible)
    provider_options: dict = field(default_factory=dict)


@dataclass
class LLMProviderConfig:
    """Configuration for LLM providers (technology-agnostic)."""
    provider: str  # "groq", "openai", "claude", "gemini"
    api_key: str
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # Provider-specific options (extensible)
    provider_options: dict = field(default_factory=dict)


@dataclass
class TTSProviderConfig:
    """Configuration for TTS providers (technology-agnostic)."""
    provider: str  # "azure", "google", "elevenlabs"
    api_key: str
    region: Optional[str] = None
    audio_mode: str = "twilio"  # "browser", "twilio", "telnyx"
    
    # Provider-specific options (extensible)
    provider_options: dict = field(default_factory=dict)
