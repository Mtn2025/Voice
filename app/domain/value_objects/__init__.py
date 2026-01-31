"""Value Objects package - Type-safe, immutable domain objects."""

from app.domain.value_objects.call_context import CallMetadata, ContactInfo
from app.domain.value_objects.voice_config import AudioFormat, AudioMode, VoiceConfig, VoiceStyle

__all__ = [
    "AudioFormat",
    "AudioMode",
    "CallMetadata",
    # Call Context
    "ContactInfo",
    # Voice Configuration
    "VoiceConfig",
    "VoiceStyle",
]
