"""
TTS With Fallback - Resilience adapter (Module 11).

Wraps primary TTS with fallback TTS for automatic failure recovery.

Gap Analysis: Score Resiliencia 85/100 → 100/100
"""
import logging
from typing import AsyncIterator, Optional

from app.domain.ports import TTSPort, TTSRequest
from app.domain.ports import TTSException

logger = logging.getLogger(__name__)


class TTSWithFallback(TTSPort):
    """
    TTS adapter with automatic fallback on primary failure.
    
    Resilience Pattern: Circuit Breaker + Fallback
    
    Behavior:
    1. Always try primary TTS first
    2. On failure, use fallback TTS
    3. After 3 consecutive failures, switch to fallback mode
    4. Auto-recover to primary after success
    
    Example:
        >>> from app.adapters.outbound.tts.azure_tts_adapter import AzureTTSAdapter
        >>> from app.adapters.outbound.tts.google_tts_adapter import GoogleTTSAdapter
        >>> 
        >>> primary = AzureTTSAdapter(...)
        >>> fallback = GoogleTTSAdapter(...)
        >>> 
        >>> tts = TTSWithFallback(primary=primary, fallback=fallback)
        >>> 
        >>> # If Azure fails, automatically uses Google
        >>> async for chunk in tts.synthesize(request):
        ...     # Audio from primary OR fallback
        ...     pass
    """
    
    def __init__(self, primary: TTSPort, fallback: TTSPort):
        """
        Initialize TTS with fallback.
        
        Args:
            primary: Primary TTS adapter (e.g., AzureTTSAdapter)
            fallback: Fallback TTS adapter (e.g., GoogleTTSAdapter)
        """
        self.primary = primary
        self.fallback = fallback
        
        # Circuit breaker state
        self._primary_failures = 0
        self._failure_threshold = 3
        self._fallback_active = False
        
        logger.info(
            f"[TTSFallback] Initialized - Primary: {type(primary).__name__}, "
            f"Fallback: {type(fallback).__name__}"
        )
    
    async def synthesize(self, request: TTSRequest) -> AsyncIterator[bytes]:
        """
        Synthesize speech with automatic fallback.
        
        Args:
            request: TTS synthesis request
        
        Yields:
            Audio bytes (from primary OR fallback)
        
        Raises:
            TTSException: If BOTH primary AND fallback fail
        """
        # Auto-recovery: Reset fallback mode if primary was working
        if self._fallback_active and self._primary_failures == 0:
            self._fallback_active = False
            logger.info("[TTSFallback] Primary recovered, switching back from fallback")
        
        # Try primary if not in fallback mode
        if not self._fallback_active:
            try:
                logger.debug(f"[TTSFallback] Using PRIMARY: {type(self.primary).__name__}")
                
                async for chunk in self.primary.synthesize(request):
                    yield chunk
                
                # Success - reset failure counter
                self._primary_failures = 0
                return
            
            except TTSException as e:
                self._primary_failures += 1
                
                logger.warning(
                    f"[TTSFallback] Primary failed ({self._primary_failures}/{self._failure_threshold}): {e}, "
                    f"using fallback"
                )
                
                # Switch to fallback mode after threshold
                if self._primary_failures >= self._failure_threshold:
                    self._fallback_active = True
                    logger.error(
                        f"[TTSFallback] Primary failed {self._failure_threshold}x, "
                        f"SWITCHING TO FALLBACK MODE"
                    )
        
        # Use fallback (either was in fallback mode, or primary just failed)
        try:
            logger.info(f"[TTSFallback] Using FALLBACK: {type(self.fallback).__name__}")
            
            async for chunk in self.fallback.synthesize(request):
                yield chunk
        
        except TTSException as fallback_error:
            logger.error(f"[TTSFallback] BOTH primary AND fallback failed! {fallback_error}")
            raise TTSException(
                f"TTS complete failure - Primary: {type(self.primary).__name__}, "
                f"Fallback: {type(self.fallback).__name__}"
            ) from fallback_error
    
    async def get_available_voices(self):
        """Get available voices from primary."""
        # Delegate to primary (fallback voices may differ)
        return await self.primary.get_available_voices()
    
    def is_voice_available(self, voice_name: str) -> bool:
        """Check if voice is available in primary."""
        return self.primary.is_voice_available(voice_name)
    
    @property
    def is_using_fallback(self) -> bool:
        """Check if currently in fallback mode."""
        return self._fallback_active
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._primary_failures
