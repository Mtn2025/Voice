"""
Google Cloud STT Adapter - Fallback option for Azure STT.

Stub implementation for fallback resilience testing.
"""
import logging
from collections.abc import Callable
from typing import Any

from app.domain.ports import STTConfig, STTEvent, STTPort, STTRecognizer

logger = logging.getLogger(__name__)


class MockSTTRecognizer(STTRecognizer):
    """Recognizer MOCK para pruebas de fallback."""

    def __init__(self, config: STTConfig):
        self.config = config
        self.callback = None

    def subscribe(self, callback: Callable[[STTEvent], None]):
        self.callback = callback

    async def start_continuous_recognition(self):
        logger.info("[GoogleSTT Mock] Started continuous recognition")

    async def stop_continuous_recognition(self):
        logger.info("[GoogleSTT Mock] Stopped continuous recognition")

    # --- Legacy Async Interface (for STTProcessor compatibility) ---
    class MockFuture:
        def get(self):
            return None

    def start_continuous_recognition_async(self):
        return self.MockFuture()

    def stop_continuous_recognition_async(self):
        return self.MockFuture()

    def write(self, audio_data: bytes):
        # Mock behavior: randomly recognize something or silence
        # In a real mock, we might analyze bytes or just log
        pass


class GoogleSTTAdapter(STTPort):
    """
    Google Cloud STT adapter (fallback implementation).
    Implements STTPort.
    """

    def __init__(self, credentials_path: str | None = None):
        self.credentials_path = credentials_path
        logger.warning("[GoogleSTT] Initialized in MOCK mode (Stub)")

    def create_recognizer(
        self,
        config: STTConfig,
        on_interruption_callback: Callable | None = None,
        event_loop: Any | None = None
    ) -> STTRecognizer:
        return MockSTTRecognizer(config)

    async def transcribe_audio(self, audio_bytes: bytes, language: str = "es") -> str:
        """Mock batch transcription."""
        return "[GoogleSTT Fallback] Mock Transcription"

    async def close(self):
        pass
