"""
Google Cloud TTS Adapter - Fallback option for Azure TTS.

Provides TTS synthesis via Google Cloud Text-to-Speech API.
"""
import logging
from typing import AsyncIterator, Optional, List

from app.domain.ports import TTSPort, TTSRequest, VoiceMetadata, TTSException

logger = logging.getLogger(__name__)


class GoogleTTSAdapter(TTSPort):
    """
    Google Cloud TTS adapter (fallback implementation).
    
    NOTE: STUB implementation (Mock Mode).
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
        self._mock_mode = True
        logger.warning("[GoogleTTS] Initialized in MOCK mode (Stub)")
    
    async def synthesize(self, request: TTSRequest) -> bytes:
        """Mock synthesis."""
        if self._mock_mode:
            logger.info(f"[GoogleTTS] Mock synthesizing: {request.text[:30]}...")
            return b'\x00' * 16000 # 1 sec silence
            
        return b''

    async def synthesize_ssml(self, ssml: str) -> bytes:
        """Mock SSML synthesis."""
        if self._mock_mode:
             logger.info(f"[GoogleTTS] Mock synthesizing SSML...")
             return b'\x00' * 16000
        return b''

    def get_available_voices(self, language: Optional[str] = None) -> List[VoiceMetadata]:
        return [
            VoiceMetadata(id="es-US-Wavenet-A", name="Google Wavenet A", gender="Female", locale="es-US")
        ]

    def get_voice_styles(self, voice_id: str) -> List[str]:
        return ["default"]

    async def close(self):
        pass
