import asyncio
import logging
from typing import Any

from app.core.frames import AudioFrame, ControlFrame, Frame, UserStartedSpeakingFrame
from app.core.processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)

class PipelineOutputSink(FrameProcessor):
    """
    Consumer of AudioFrames. Delegates actual sending to the Orchestrator
    to preserve background sound mixing logic.
    Generic Sink for all transports (Simulator, Twilio, Telnyx).
    """
    def __init__(self, orchestrator: Any):
        super().__init__(name="PipelineOutputSink")
        self.orchestrator = orchestrator
        self._queue = asyncio.Queue()
        self._worker_task = asyncio.create_task(self._worker())

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                # Anti-Echo: Do not play back user input
                if frame.metadata.get('source') == 'user_input':
                    return

                # Queue audio for background sending (Non-blocking)
                await self._queue.put(frame)

            elif isinstance(frame, UserStartedSpeakingFrame):
                 # Critical: Trigger Barge-in Logic
                 await self.orchestrator.interrupt_speaking()
                 # Also clear our own sink queue
                 while not self._queue.empty():
                     try:
                        self._queue.get_nowait()
                        self._queue.task_done()
                     except asyncio.QueueEmpty:
                        break
                     except Exception:
                        pass

            elif isinstance(frame, ControlFrame):
                # Other control frames
                await self.push_frame(frame, direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _worker(self):
        """Background worker to consume audio frames with pacing."""
        while True:
            try:
                frame = await self._queue.get()
                await self._send_audio(frame)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sink Worker Error: {e}")

    async def _send_audio(self, frame: AudioFrame):
        # Delegate to orchestrator's buffered sender
        try:
            # [TRACING] Log Audio Out to User
            logger.debug(f"📢 [AUDIO_OUT] Sending {len(frame.data)} bytes to User")
            await self.orchestrator.send_audio_chunked(frame.data)
        except Exception as e:
            logger.error(f"Error in PipelineOutputSink delegation: {e}")

    async def cleanup(self):
        if self._worker_task:
            self._worker_task.cancel()
        await super().cleanup()

    def set_stream_id(self, stream_id: str):
        # Orchestrator handles stream ID context
        pass
