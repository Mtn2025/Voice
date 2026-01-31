import logging
import time
from typing import Any

from app.core.frames import AudioFrame, Frame, UserStoppedSpeakingFrame
from app.core.processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)

class MetricsProcessor(FrameProcessor):
    """
    Tracks pipeline latency metrics.
    Specifically measures "Time to First Audio" (TTFA) after User Stopped Speaking.
    """
    def __init__(self, config: Any):
        super().__init__(name="MetricsProcessor")
        self.config = config
        self.last_user_stop_time = 0.0
        self.turn_in_progress = False

    async def process_frame(self, frame: Frame, direction: int):
        current_time = time.time()

        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, UserStoppedSpeakingFrame):
                self.last_user_stop_time = current_time
                self.turn_in_progress = True

            elif isinstance(frame, AudioFrame) and self.turn_in_progress:
                # First chunk of audio after user stopped -> TTFA
                latency_ms = (current_time - self.last_user_stop_time) * 1000
                logger.info(f"⚡ [LATENCY] TTFA (Turn Latency): {latency_ms:.0f}ms")
                self.turn_in_progress = False # Reset for next turn

            # Pass through
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)
