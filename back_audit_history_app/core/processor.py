import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from app.core.frames import Frame

class FrameDirection:
    DOWNSTREAM = 1
    UPSTREAM = 2

class FrameProcessor(ABC):
    """
    Base class for any element in the pipeline processing chain.
    """
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self._next: Optional['FrameProcessor'] = None
        self._prev: Optional['FrameProcessor'] = None

    def link(self, processor: 'FrameProcessor'):
        """Connect this processor to the next one."""
        self._next = processor
        processor._prev = self

    @abstractmethod
    async def process_frame(self, frame: Frame, direction: int):
        """
        Process a frame. Must be implemented by subclasses.
        Use push_frame() to send results to the next processor.
        """
        pass

    async def push_frame(self, frame: Frame, direction: int = FrameDirection.DOWNSTREAM):
        """Send a frame to the next processor in the chain."""
        if direction == FrameDirection.DOWNSTREAM:
            if self._next:
                await self._next.process_frame(frame, direction)
        elif direction == FrameDirection.UPSTREAM:
            if self._prev:
                await self._prev.process_frame(frame, direction)

    async def cleanup(self):
        """Release resources."""
        pass
