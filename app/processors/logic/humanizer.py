import logging
import random

from app.core.frames import Frame, TextFrame
from app.core.processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)

class HumanizerProcessor(FrameProcessor):
    """
    Consumes TextFrames from LLM.
    Injects "human" elements like fillers (muletillas) if enabled in config.
    Passes modified TextFrame to TTS.
    """
    def __init__(self, config):
        super().__init__(name="HumanizerProcessor")
        self.config = config
        self.fillers = ["eh...", "hmm...", "este...", "pues..."]
        self.last_turn_role = None

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM: # LLM -> TTS
            if isinstance(frame, TextFrame):
                await self._process_text_frame(frame)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _process_text_frame(self, frame: TextFrame):
        """
        Injects fillers if configured.
        """
        text = frame.text

        # Check config
        enabled = getattr(self.config, 'voice_filler_injection', False)

        # 20% chance injection for chunks > 10 chars
        if enabled and text and len(text) > 10 and random.random() < 0.2:
            filler = random.choice(self.fillers)
            logger.info(f"🗣️ [HUMANIZER] Injecting filler: '{filler}'")
            text = f"{filler} {text}"

        # Create new frame or modify existing? TextFrame is likely immutable dataclass?
        # Check frames.py definition. Usually standard classes.
        # Let's create new frame to be safe.
        new_frame = TextFrame(text=text)
        await self.push_frame(new_frame, FrameDirection.DOWNSTREAM)
