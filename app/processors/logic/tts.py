import asyncio
import contextlib
import logging
from typing import Any

from app.core.frames import AudioFrame, CancelFrame, Frame, TextFrame
from app.core.processor import FrameDirection, FrameProcessor
from app.domain.ports import TTSPort, TTSRequest

logger = logging.getLogger(__name__)


class TTSProcessor(FrameProcessor):
    """
    Consumes TextFrames, calls TTS Port (Hexagonal), produces AudioFrames.
    Supports cancellation via CancelFrame.
    Implements true streaming for low latency.
    """
    def __init__(self, tts_port: TTSPort, config: Any):
        super().__init__(name="TTSProcessor")
        self.tts_port = tts_port
        self.config = config

        # Backpressure configuration
        self.backpressure_threshold = getattr(config, 'tts_backpressure_threshold', 3)

        # Concurrency: Internal Queue for serial synthesis
        self._tts_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

        # Flags
        self._is_running = False

    async def start(self):
        """Start the TTS processing worker."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("🔊 [TTS] Worker started")

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, TextFrame):
                # Ensure worker is running (defensive programming)
                if not self._is_running:
                    await self.start()

                await self._tts_queue.put((frame.text, frame.trace_id))

            elif isinstance(frame, CancelFrame):
                logger.info("🛑 [TTS] Received CancelFrame. Clearing queue.")
                await self._clear_queue()
                await self.push_frame(frame, direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _worker(self):
        """Sequential TTS Worker Loop."""
        while self._is_running:
            try:
                text, trace_id = await self._tts_queue.get()

                # --- Response Pacing (Profile Config) ---
                client_type = getattr(self.config, 'client_type', 'twilio')
                profile = self.config.get_profile(client_type)

                delay = profile.response_delay_seconds or 0.0

                if delay > 0:
                    logger.debug(f"⏳ [TTS] Pacing: Waiting {delay}s...")
                    await asyncio.sleep(delay)
                # ----------------------------------------

                await self._synthesize(text, trace_id)
                self._tts_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"TTS Worker Error: {e}")

    async def _clear_queue(self):
        """Flush pending texts and restart worker logic if needed."""
        # Empty the queue
        while not self._tts_queue.empty():
            try:
                self._tts_queue.get_nowait()
                self._tts_queue.task_done()
            except asyncio.QueueEmpty:
                break

        # Note: We rely on the Port implementation to handle cancellation of active properties
        # For true cancellation, we might need a flag or restart the worker
        # Restarting worker is the safest way to kill active synthesis
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

            # Restart
            if self._is_running:
                self._worker_task = asyncio.create_task(self._worker())

    async def _synthesize(self, text: str, trace_id: str):
        if not text:
            return

        logger.info(f"🗣️ [TTS] trace={trace_id} Synthesizing: {text}")

        try:
            # Backpressure Check
            queue_depth = self._tts_queue.qsize()
            backpressure_detected = queue_depth >= self.backpressure_threshold

            if backpressure_detected:
                logger.warning(f"⚠️ [TTS] Backpressure detected: queue={queue_depth}")

            # Request
            request = TTSRequest(
                text=text,
                voice_id=getattr(self.config, 'voice_name', 'en-US-JennyNeural'),
                language=getattr(self.config, 'language', 'es-MX'),
                speed=getattr(self.config, 'voice_speed', 1.0),
                pitch=getattr(self.config, 'voice_pitch', 0.0),
                volume=getattr(self.config, 'voice_volume', 100.0),
                style=getattr(self.config, 'voice_style', None),
                backpressure_detected=backpressure_detected,
                metadata={"trace_id": trace_id}
            )

            # Determine correct sample rate
            sr = 16000 if getattr(self.config, 'client_type', 'twilio') == 'browser' else 8000

            # True Streaming: Emit processing audio chunks as they arrive
            # This reduces TTFB (Time To First Byte) significantly

            async for audio_chunk in self.tts_port.synthesize_stream(request):
                # We can batch small chunks if needed, or send raw
                # Sending immediately for best latency
                if audio_chunk:
                   await self.push_frame(
                       AudioFrame(data=audio_chunk, sample_rate=sr, channels=1)
                   )

            # Note: We don't log "Received X bytes" total anymore since we stream
            logger.debug(f"🗣️ [TTS] trace={trace_id} Synthesis complete")

        except Exception as e:
            logger.error(f"TTS Error: {e}", exc_info=True)

    async def stop(self):
        """Stops the TTS processor and cleans up tasks."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None
        await super().stop()
