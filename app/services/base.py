from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, Tuple

class AbstractSTT(ABC):
    @abstractmethod
    def create_recognizer(self, language: str = "es-MX") -> Tuple[Any, Any]:
        """Returns (recognizer_instance, audio_stream)"""
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
