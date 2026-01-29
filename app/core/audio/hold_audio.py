"""
Hold Audio Player - UX improvement for async operations.

Plays subtle 'thinking' audio loop during tool execution
to prevent perception of system freezing.

Módulo 10: Gap Analysis - Hold Audio Feature
"""
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class HoldAudioPlayer:
    """
    Play 'thinking' sounds during async operations (e.g., tool execution).
    
    UX Problem: During tool execution (2-5s), client hears silence →
    perception of "system frozen".
    
    Solution: Play subtle periodic sound (500ms loop) to indicate
    "system is processing".
    
    Example:
        >>> player = HoldAudioPlayer()
        >>> await player.start()
        >>> # ... async operation (tool execution) ...
        >>> await player.stop()
    """
    
    def __init__(self):
        """Initialize hold audio player."""
        self._playing = False
        self._task: Optional[asyncio.Task] = None
        self._sound_interval = 0.8  # 800ms between "thinking" indicators
    
    async def start(self):
        """
        Start playing hold audio loop.
        
        Non-blocking: Returns immediately, audio plays in background.
        """
        if self._playing:
            logger.debug("[HoldAudio] Already playing, ignoring start()")
            return
        
        logger.info("[HoldAudio] Starting thinking audio loop")
        self._playing = True
        self._task = asyncio.create_task(self._play_loop())
    
    async def stop(self):
        """
        Stop hold audio.
        
        Cancels background task gracefully.
        """
        if not self._playing:
            return
        
        logger.info("[HoldAudio] Stopping thinking audio")
        self._playing = False
        
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Expected
    
    async def _play_loop(self):
        """
        Play thinking sound in loop.
        
        Currently: Logs thinking indicator (audio integration TODO).
        
        Future: Generate actual audio tone (sine wave 440Hz, 100ms duration)
        and push via AudioFrame to client.
        """
        try:
            loop_count = 0
            while self._playing:
                loop_count += 1
                
                # TODO (Future): Generate actual audio
                # audio_chunk = self._generate_thinking_tone()
                # await self.audio_manager.send_audio_chunked(audio_chunk)
                
                # Current: Log indicator
                logger.debug(f"[HoldAudio] 🤔 Thinking... ({loop_count})")
                
                # Wait before next indicator
                await asyncio.sleep(self._sound_interval)
        
        except asyncio.CancelledError:
            logger.debug("[HoldAudio] Play loop cancelled")
            raise
        except Exception as e:
            logger.error(f"[HoldAudio] Error in play loop: {e}")
    
    def _generate_thinking_tone(self) -> bytes:
        """
        Generate subtle thinking tone (sine wave).
        
        Returns:
            Audio bytes (PCM, 8000Hz, mono, 100ms duration)
        
        TODO: Implement actual audio generation
        """
        # Placeholder
        # In production: Generate 440Hz sine wave, 100ms, 8000Hz sample rate
        return b""
    
    @property
    def is_playing(self) -> bool:
        """Check if hold audio is currently playing."""
        return self._playing
