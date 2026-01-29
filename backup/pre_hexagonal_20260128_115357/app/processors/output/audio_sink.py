import asyncio
import logging
from typing import Any

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, AudioFrame, ControlFrame

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
                # Queue audio for background sending (Non-blocking)
                await self._queue.put(frame)
                
            elif isinstance(frame, UserStartedSpeakingFrame):
                 # Critical: Trigger Barge-in Logic
                 await self.orchestrator.interrupt_speaking()
                 # Also clear our own sink queue
                 # Logic for clearing sink queue might be needed here or handled by orchestrator?
                 # Since we have an internal worker, we should clear _queue too.
                 while not self._queue.empty():
                     try:
                        self._queue.get_nowait()
                        self._queue.task_done()
                     except:
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
            # logger.info(f"🎤 [SINK] Sending Audio Chunk: {len(frame.data)} bytes") # Verbose
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
