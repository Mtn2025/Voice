from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

class STTResultReason(Enum):
    RECOGNIZING_SPEECH = "recognizing_speech"
    RECOGNIZED_SPEECH = "recognized_speech"
    NO_MATCH = "no_match"
    CANCELED = "canceled"
    UNKNOWN = "unknown"

@dataclass
class STTEvent:
    reason: STTResultReason
    text: str
    duration: float = 0.0
    error_details: str = ""

class STTProvider(ABC):
    @abstractmethod
    def create_recognizer(self, language: str = "es-MX", audio_mode: str = "twilio", on_interruption_callback=None, event_loop=None) -> Any:
        """Returns a recognizer interface (wrapper or specific)."""
        pass

    @abstractmethod
    async def stop_recognition(self):
        pass

class LLMProvider(ABC):
    @abstractmethod
    async def get_stream(self, messages: list, system_prompt: str, temperature: float, max_tokens: int = 600, model: Optional[str] = None) -> AsyncGenerator[str, None]:
        pass

class TTSProvider(ABC):
    @abstractmethod
    def create_synthesizer(self, voice_name: str, audio_mode: str = "twilio") -> Any:
        pass

    @abstractmethod
    async def synthesize_ssml(self, synthesizer: Any, ssml: str) -> bytes:
        """Synthesizes SSML to audio bytes."""
        pass

# Aliases for backward compatibility if needed (though we encourage using the new names)
AbstractSTT = STTProvider
AbstractLLM = LLMProvider
AbstractTTS = TTSProvider
