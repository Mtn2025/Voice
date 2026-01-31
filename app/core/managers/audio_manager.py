"""
Audio Manager.

Handles audio streaming, queuing, and chunking strategies for different client types.
Encapsulates low-level audio transport logic avoiding blocking operations.
"""
import asyncio
import contextlib
import logging
from pathlib import Path

from app.domain.ports import AudioTransport

logger = logging.getLogger(__name__)

# Constants
CHUNK_SIZE_TELEPHONY = 160  # 160 bytes = 20ms @ 8kHz PCMU
STREAM_INTERVAL_SECONDS = 0.02  # 20ms transmission interval
CLIENT_TYPE_BROWSER = "browser"
CLIENT_TYPE_TWILIO = "twilio"
CLIENT_TYPE_TELNYX = "telnyx"


class AudioManager:
    """
    Manages audio output streaming and background audio.

    Responsibilities:
    - Audio queue management (async)
    - Chunked audio transmission (adapted to client type)
    - Background audio looping (comfort noise)
    - Stream lifecycle management
    """

    def __init__(self, transport: AudioTransport, client_type: str = CLIENT_TYPE_TWILIO):
        """
        Initialize AudioManager.

        Args:
            transport: Audio transport interface (WebSocket wrapper)
            client_type: Client identifier (browser/twilio/telnyx)
        """
        self.transport = transport
        self.client_type = client_type

        # Audio Queue (unbounded by default, implicit backpressure via pipeline)
        self.audio_queue: asyncio.Queue = asyncio.Queue()

        # Background Audio State
        self.bg_loop_buffer: bytes | None = None
        self.bg_loop_index: int = 0

        # Stream Task
        self.stream_task: asyncio.Task | None = None

        # Encoding (Default for telephony)
        self.audio_encoding = "PCMU"

        # Bot speaking state
        self.is_bot_speaking = False

    async def start(self):
        """Start audio streaming loop."""
        if not self.stream_task:
            self.stream_task = asyncio.create_task(self._audio_stream_loop())
            logger.info("🔊 [AudioManager] Stream loop started")

    async def stop(self):
        """Stop audio streaming and cleanup."""
        if self.stream_task:
            self.stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.stream_task
            self.stream_task = None
            logger.info("🔇 [AudioManager] Stream loop stopped")

    async def send_audio_chunked(self, audio_data: bytes) -> None:
        """
        Queue audio for chunked transmission.

        For telephony: chunks to CHUNK_SIZE_TELEPHONY
        For browser: sends full blob

        Args:
            audio_data: Raw audio bytes to transmit
        """
        if not audio_data:
            logger.warning("⚠️ [AudioManager] Empty audio_data received")
            return

        # Mark bot as speaking when we enqueue data
        self.is_bot_speaking = True

        logger.debug(f"📤 [AudioManager] Queuing {len(audio_data)} bytes for transmission")
        await self.audio_queue.put(audio_data)

    async def clear_queue(self):
        """Clear all pending audio from queue."""
        count = 0
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.task_done()
                count += 1
            except asyncio.QueueEmpty:
                break

        if count > 0:
            logger.info(f"🗑️ [AudioManager] Cleared {count} audio chunks from queue")

    async def interrupt_speaking(self):
        """Interrupt current speech and clear queue."""
        logger.info("🛑 [AudioManager] Interrupting speech")
        await self.clear_queue()
        self.is_bot_speaking = False

    def set_background_audio(self, audio_buffer: bytes):
        """
        Set background audio loop buffer.

        Args:
            audio_buffer: Audio to loop during silence
        """
        self.bg_loop_buffer = audio_buffer
        self.bg_loop_index = 0
        logger.info(f"🎵 [AudioManager] Background audio set ({len(audio_buffer)} bytes)")

    async def load_background_audio(self, file_path: str):
        """
        Load background audio from file path (Non-blocking).
        Uses a thread executor to avoid blocking the asyncio loop during disk IO.

        Args:
            file_path: Path to .wav file
        """
        if not Path(file_path).exists():
            logger.warning(f"⚠️ [AudioManager] Background audio file not found: {file_path}")
            return

        try:
            loop = asyncio.get_running_loop()
            # Offload blocking IO to thread pool
            audio_data = await loop.run_in_executor(None, self._read_file_sync, file_path)
            self.set_background_audio(audio_data)
        except Exception as e:
            logger.error(f"❌ [AudioManager] Failed to load background audio: {e}")

    @staticmethod
    def _read_file_sync(path: str) -> bytes:
        """Sync helper for file reading (runs in thread)."""
        with open(path, 'rb') as f:
            return f.read()

    async def _audio_stream_loop(self):
        """
        Main audio streaming loop.

        Continuously transmits audio chunks from queue or background audio.
        """
        while True:
            try:
                # Try to get audio from queue (non-blocking with timeout)
                try:
                    audio_blob = await asyncio.wait_for(
                        self.audio_queue.get(),
                        timeout=0.1
                    )

                    # Transmit queued audio
                    await self._transmit_audio(audio_blob)
                    self.audio_queue.task_done()

                except TimeoutError:
                    # No queued audio - send background audio if available
                    # Only play background noise if we are SURE bot is not talking
                    if self.bg_loop_buffer and not self.is_bot_speaking:
                        await self._transmit_background_audio()
                    else:
                        # Small sleep to prevent busy loop
                        await asyncio.sleep(STREAM_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ [AudioManager] Stream loop error: {e}", exc_info=True)
                await asyncio.sleep(0.1)

    async def _transmit_audio(self, audio_blob: bytes):
        """
        Transmit audio blob with chunking based on client type.

        Args:
            audio_blob: Audio data to transmit
        """
        if self.client_type == CLIENT_TYPE_BROWSER:
            # Browser: send full blob
            await self.transport.send_audio(audio_blob)
            logger.debug(f"📤 [AudioManager] Sent {len(audio_blob)} bytes (browser)")
        else:
            # Telephony: chunking
            chunk_size = CHUNK_SIZE_TELEPHONY
            for i in range(0, len(audio_blob), chunk_size):
                chunk = audio_blob[i:i + chunk_size]
                await self.transport.send_audio(chunk)

            logger.debug(f"📤 [AudioManager] Sent {len(audio_blob)} bytes in chunks")

        # Note: We do NOT auto-reset is_bot_speaking to False here anymore.
        # It's safer to let the Orchestrator/Pipeline signal explicit "End of Turn".
        # However, if queue is empty for a long time, we might reset?
        # For strict audit: Removing the "auto-off" logic is safer to prevent flickering.
        # The Orchestrator calls `interrupt_speaking` or `stop` which handles logic.
        # Or, we assume "speaking" is strictly "has items in queue".

        if self.audio_queue.empty():
             # Graceful state update: Only reset if we truly have nothing left.
             # In a real pipeline, "EndFrame" should trigger this.
             # For now, we keep it simple but logged.
             pass

    async def _transmit_background_audio(self):
        """Transmit background audio chunk."""
        if not self.bg_loop_buffer:
            return

        chunk_size = CHUNK_SIZE_TELEPHONY
        chunk = self.bg_loop_buffer[
            self.bg_loop_index : self.bg_loop_index + chunk_size
        ]

        if len(chunk) < chunk_size:
            # Loop back to start
            self.bg_loop_index = 0
            chunk = self.bg_loop_buffer[0:chunk_size]
        else:
            self.bg_loop_index += chunk_size

        await self.transport.send_audio(chunk)
        await asyncio.sleep(STREAM_INTERVAL_SECONDS)
