import logging
from abc import ABC, abstractmethod
from enum import IntEnum

from app.core.frames import Frame

# Configure logging
logger = logging.getLogger(__name__)

class FrameDirection(IntEnum):
    DOWNSTREAM = 1
    UPSTREAM = 2

class FrameProcessor(ABC):
    """
    Base class for any element in the pipeline processing chain.
    """
    def __init__(self, name: str | None = None):
        self.name = name or self.__class__.__name__
        self._next: FrameProcessor | None = None
        self._prev: FrameProcessor | None = None

    def link(self, processor: 'FrameProcessor'):
        """Connect this processor to the next one."""
        self._next = processor
        processor._prev = self

    async def start(self):  # noqa: B027 - Optional hook for subclasses
        """
        Initialize resources or background tasks.
        Override this method if the processor needs async startup logic.
        """
        pass

    @abstractmethod
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """
        Process a frame. Must be implemented by subclasses.
        Use push_frame() to send results to the next processor.
        """
        pass

    async def push_frame(self, frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM):
        """Send a frame to the next processor in the chain."""
        if direction == FrameDirection.DOWNSTREAM:
            if self._next:
                await self._next.process_frame(frame, direction)
            else:
                logger.debug(f"[{self.name}] Dropped DOWNSTREAM frame (End of Chain): {frame}")
        elif direction == FrameDirection.UPSTREAM:
            if self._prev:
                await self._prev.process_frame(frame, direction)
            else:
                logger.debug(f"[{self.name}] Dropped UPSTREAM frame (Start of Chain): {frame}")

    async def cleanup(self):  # noqa: B027 - Optional hook for subclasses
        """Release resources."""
        pass
