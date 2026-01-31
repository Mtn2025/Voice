"""
Hold Audio Player.

Plays subtle 'thinking' audio loop during long async operations (e.g., tool execution)
to prevent the user from perceiving the system as frozen.
"""
import asyncio
import contextlib
import logging

# To avoid circular imports, use TYPE_CHECKING for type hints if needed,
# or just type as 'Any' if the manager is passed dynamically.
# Ideally, we import the class if possible.
from app.core.managers.audio_manager import AudioManager

logger = logging.getLogger(__name__)


class HoldAudioPlayer:
    """
    Play 'thinking' sounds during async operations.

    Prevents "dead air" on the phone line during long latencies.
    Generates a synthetic "comfort noise" or pulse to keep the stream active.
    """

    def __init__(self, audio_manager: AudioManager):
        """
        Initialize hold audio player.

        Args:
            audio_manager: Reference to the audio manager to send frames to.
        """
        self.audio_manager = audio_manager
        self._playing = False
        self._task: asyncio.Task | None = None
        self._sound_interval = 2.0  # 2 seconds between pulses

        # Pre-synthesize a short "tick" or "comfort pulse" (20ms)
        # 8000Hz, PCMU (u-law) approximation or silence + tick
        # Note: Proper PCMU synthesis requires a lookup table or math.
        # For safety/simplicity, we generate 20ms of simple silence/low-noise.
        # 0xFF is silence in u-law.
        self._pulse_audio = b'\xff' * 160  # 20ms silence (keep line active)

    async def start(self):
        """
        Start playing hold audio loop.

        Non-blocking: Returns immediately, audio plays in background.
        """
        if self._playing:
            return

        logger.debug("[HoldAudio] Starting keep-alive loop")
        self._playing = True
        self._task = asyncio.create_task(self._play_loop())

    async def stop(self):
        """
        Stop hold audio.
        """
        if not self._playing:
            return

        logger.debug("[HoldAudio] Stopping keep-alive loop")
        self._playing = False

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _play_loop(self):
        """
        Loop sending comfort packets to Audio Manager.
        """
        try:
            while self._playing:
                # Send a keep-alive chunk (comfort noise/silence)
                await self.audio_manager.send_audio_chunked(self._pulse_audio)

                # Wait for next interval
                await asyncio.sleep(self._sound_interval)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[HoldAudio] Error in play loop: {e}", exc_info=True)

    @property
    def is_playing(self) -> bool:
        """Check if hold audio is currently playing."""
        return self._playing
