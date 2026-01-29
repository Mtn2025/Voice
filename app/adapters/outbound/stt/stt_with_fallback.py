"""
Fallback Wrapper for STT Port - Graceful Degradation.

Implements automatic failover for speech recognition.
"""
import logging
from typing import Optional, Callable, Any
from app.domain.ports import STTPort, STTConfig, STTRecognizer, STTException


logger = logging.getLogger(__name__)


class STTWithFallback(STTPort):
    """
    STT Port wrapper with graceful degradation.
    
    Falls back to alternative STT provider on failures.
    """
    
    def __init__(self, primary: STTPort, fallback: Optional[STTPort] = None):
        """
        Args:
            primary: Primary STT provider (e.g., Azure)
            fallback: Fallback provider (e.g., Groq Whisper)
        """
        self.primary = primary
        self.fallback = fallback
    
    def create_recognizer(
        self,
        config: STTConfig,
        on_interruption_callback: Optional[Callable] = None,
        event_loop: Optional[Any] = None
    ) -> STTRecognizer:
        """
        Create recognizer from primary, fallback on failure.
        """
        try:
            logger.info("[STT Fallback] Creating recognizer with primary")
            return self.primary.create_recognizer(
                config, on_interruption_callback, event_loop
            )
        
        except STTException as e:
            if not e.retryable or not self.fallback:
                raise
            
            logger.warning(f"[STT Fallback] Primary failed: {e}. Trying fallback...")
            return self.fallback.create_recognizer(
                config, on_interruption_callback, event_loop
            )
    
    async def transcribe_audio(self, audio_bytes: bytes, language: str = "es") -> str:
        """
        Transcribe with primary, fallback on failure.
        """
        try:
            return await self.primary.transcribe_audio(audio_bytes, language)
        
        except STTException as e:
            if not e.retryable or not self.fallback:
                raise
            
            logger.warning(f"[STT Fallback] Primary transcription failed. Using fallback...")
            return await self.fallback.transcribe_audio(audio_bytes, language)
    
    async def close(self):
        """Close both providers."""
        await self.primary.close()
        if self.fallback:
            await self.fallback.close()
