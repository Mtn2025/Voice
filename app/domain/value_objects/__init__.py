"""Value Objects package - Type-safe, immutable domain objects."""

from app.domain.value_objects.voice_config import VoiceConfig, AudioFormat, VoiceStyle, AudioMode
from app.domain.value_objects.call_context import ContactInfo, CallMetadata

__all__ = [
    # Voice Configuration
    "VoiceConfig",
    "AudioFormat",
    "VoiceStyle",
    "AudioMode",
    
    # Call Context
    "ContactInfo",
    "CallMetadata",
]
