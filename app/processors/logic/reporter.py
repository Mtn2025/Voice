import logging
from collections.abc import Awaitable, Callable

from app.core.frames import Frame, TextFrame
from app.core.processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)

class TranscriptReporter(FrameProcessor):
    """
    Passive processor that reports TextFrames to a callback (e.g. WebSocket)
    without modifying the frame flow.
    """
    def __init__(self, callback: Callable[[str, str], Awaitable[None]], role_label: str = "assistant"):
        super().__init__(name=f"TranscriptReporter-{role_label}")
        self.callback = callback
        self.role_label = role_label

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM and isinstance(frame, TextFrame) and frame.text:
            logger.info(f"📜 [REPORTER] {self.role_label.upper()}: {frame.text}")
            await self.callback(self.role_label, frame.text)

        # Always push downstream
        await self.push_frame(frame, direction)
