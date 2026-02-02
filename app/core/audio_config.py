from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class AudioConfig:
    """
    Configuration object for audio format details.
    Decouples adapters from string-based 'client_type' or 'audio_mode'.
    """
    sample_rate: int
    encoding: Literal["pcm", "mulaw", "alaw"]
    channels: int
    bits_per_sample: int = 16

    @staticmethod
    def for_browser() -> "AudioConfig":
        """Configuration for Browser usage (High Quality)."""
        return AudioConfig(
            sample_rate=16000,
            encoding="pcm",
            channels=1,
            bits_per_sample=16
        )

    @staticmethod
    def for_telnyx() -> "AudioConfig":
        """Configuration for Telnyx (Telephony Standard)."""
        return AudioConfig(
            sample_rate=8000,
            encoding="mulaw", # Usually PCMU/8000
            channels=1,
            bits_per_sample=8
        )

    @staticmethod
    def for_twilio() -> "AudioConfig":
        """Configuration for Twilio (Telephony Standard)."""
        return AudioConfig(
            sample_rate=8000,
            encoding="mulaw", # PCMU/8000
            channels=1,
            bits_per_sample=8
        )

    @staticmethod
    def from_legacy_mode(mode: str) -> "AudioConfig":
        """Helper to convert legacy string modes."""
        if mode == "browser":
            return AudioConfig.for_browser()
        elif mode == "telnyx":
            return AudioConfig.for_telnyx()
        else:
            # Default to Twilio/Telephony
            return AudioConfig.for_twilio()
