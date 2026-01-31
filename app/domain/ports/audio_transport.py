from abc import ABC, abstractmethod
from typing import Any


class AudioTransport(ABC):
    """
    Port (Interface) for sending Audio and Control messages to a client.
    Implementations (Adapters) will handle WebSocket, SIP, or other protocols.
    """
    @abstractmethod
    async def send_audio(self, audio_data: bytes, sample_rate: int = 8000) -> None:
        """Send audio data to the client."""
        pass

    @abstractmethod
    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON control message to the client."""
        pass

    @abstractmethod
    def set_stream_id(self, stream_id: str) -> None:
        """Set Stream/Call ID for protocol wrapping."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connectivity."""
        pass
