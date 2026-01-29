"""
Google Cloud STT Adapter - Fallback option for Azure STT (Module 12).

Stub implementation for fallback resilience testing.
"""
import logging
from typing import AsyncIterator

from app.domain.ports import STTPort, STTRequest, STTResponse
from app.domain.exceptions.stt_exceptions import STTException

logger = logging.getLogger(__name__)


class GoogleSTTAdapter(STTPort):
    """
    Google Cloud STT adapter (fallback for Azure).
    
    NOTE: STUB implementation (mock mode).
    Returns mock transcriptions for fallback testing.
    """
    
    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path
        self._mock_mode = True
        
        if self._mock_mode:
            logger.warning("[GoogleSTT] Running in MOCK mode - returning mock transcriptions")
    
    async def transcribe(self, request: STTRequest) -> AsyncIterator[STTResponse]:
        """Mock transcription."""
        if self._mock_mode:
            logger.info("[GoogleSTT] MOCK transcription (fallback mode)")
            
            # Yield mock partial transcription
            yield STTResponse(
                text="[Google STT Mock]",
                is_final=False,
                confidence=0.85
            )
            
            # Yield final transcription
            yield STTResponse(
                text="[Google STT Fallback] Mock transcription",
                is_final=True,
                confidence=0.90
            )
