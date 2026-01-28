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
        
    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                await self._send_audio(frame)
            elif isinstance(frame, ControlFrame):
                await self.push_frame(frame, direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _send_audio(self, frame: AudioFrame):
        # Delegate to orchestrator's buffered sender
        try:
            # logger.info(f"🎤 [SINK] Sending Audio Chunk: {len(frame.data)} bytes") # Verbose
            await self.orchestrator.send_audio_chunked(frame.data)
        except Exception as e:
            logger.error(f"Error in PipelineOutputSink delegation: {e}")

    def set_stream_id(self, stream_id: str):
        # Orchestrator handles stream ID context
        pass
