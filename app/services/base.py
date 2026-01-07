from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Callable
from enum import Enum
from dataclasses import dataclass

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


class AbstractSTT(ABC):
    @abstractmethod
    @abstractmethod
    def create_recognizer(self, language: str = "es-MX", audio_mode: str = "twilio", on_interruption_callback=None, event_loop=None) -> Any:
        """Returns a recognizer interface (wrapper or specific)."""
        pass
    
    @abstractmethod
    async def stop_recognition(self):
        pass

class AbstractLLM(ABC):
    @abstractmethod
    async def get_stream(self, messages: list, system_prompt: str, temperature: float) -> AsyncGenerator[str, None]:
        pass

class AbstractTTS(ABC):
    @abstractmethod
    def create_synthesizer(self, voice_name: str) -> Any:
        pass

    @abstractmethod
    async def synthesize_stream(self, text: str) -> bytes:
        """Yields audio bytes or returns full buffer"""
        pass
