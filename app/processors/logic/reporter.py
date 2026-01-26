import logging
from typing import Callable, Coroutine

from app.core.frames import Frame, TextFrame
from app.core.processor import FrameProcessor, FrameDirection

logger = logging.getLogger(__name__)

class TranscriptReporter(FrameProcessor):
    """
    Passive processor that reports TextFrames to a callback (e.g. WebSocket)
    without modifying the frame flow.
    """
    def __init__(self, callback: Callable[[str, str], Coroutine], role_label: str = "assistant"):
        super().__init__(name=f"TranscriptReporter-{role_label}")
        self.callback = callback
        self.role_label = role_label

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, TextFrame):
                # We assume TextFrame contains valid speech/text
                if frame.text:
                    await self.callback(self.role_label, frame.text)
        
        # Always push downstream
        await self.push_frame(frame, direction)
