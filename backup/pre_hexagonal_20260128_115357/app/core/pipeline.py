import asyncio
import logging
from typing import List, Callable, Coroutine

from app.core.frames import Frame, SystemFrame
from app.core.processor import FrameProcessor, FrameDirection

# Configure logging
logger = logging.getLogger(__name__)

class PipelineSource(FrameProcessor):
    """Entry point of the pipeline."""
    def __init__(self, upstream_handler: Callable[[Frame], Coroutine]):
        super().__init__(name="PipelineSource")
        self._upstream_handler = upstream_handler

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.UPSTREAM:
            # Frame coming from inside the pipeline going out/up
            await self._upstream_handler(frame)
        else:
            # Frame going into the pipeline (start/downstream)
            await self.push_frame(frame, direction)

class PipelineSink(FrameProcessor):
    """Exit point of the pipeline."""
    def __init__(self, downstream_handler: Callable[[Frame], Coroutine]):
        super().__init__(name="PipelineSink")
        self._downstream_handler = downstream_handler

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            # Frame reached the end of the pipeline
            await self._downstream_handler(frame)
        else:
            # Frame coming from outside going up the pipeline
            await self.push_frame(frame, direction)

class Pipeline(FrameProcessor):
    """
    Orchestrates a linear chain of FrameProcessors.
    Manages the asyncio loop for processing frames in priority order.
    """
    def __init__(self, processors: List[FrameProcessor]):
        super().__init__(name="Pipeline")
        self._source = PipelineSource(self._handle_upstream)
        self._sink = PipelineSink(self._handle_downstream)
        
        # Build the chain: Source -> [Processors] -> Sink
        self._processors = [self._source] + processors + [self._sink]
        self._link_processors()
        
        # Priority Queue: (priority, counter, frame, direction)
        # Priority 1 (System) < Priority 2 (Data)
        self._queue = asyncio.PriorityQueue()
        self._running = False
        self._task = None
        self._counter = 0 # To ensuring stable ordering for equal priorities

    def _link_processors(self):
        prev = self._processors[0]
        for curr in self._processors[1:]:
            prev.link(curr)
            prev = curr

    async def start(self):
        """Start the pipeline processing loop."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.info("Pipeline started.")

    async def stop(self):
        """Stop the pipeline and cleanup processors."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        for p in self._processors:
            await p.cleanup()
        logger.info("Pipeline stopped.")

    async def queue_frame(self, frame: Frame, direction: int = FrameDirection.DOWNSTREAM):
        """Add a frame to the processing queue."""
        priority = 1 if isinstance(frame, SystemFrame) else 2
        self._counter += 1
        await self._queue.put((priority, self._counter, frame, direction))

    async def _process_queue(self):
        """Main loop consuming frames from the queue."""
        while self._running:
            try:
                priority, _, frame, direction = await self._queue.get()
                
                # Route the frame to the appropriate entry point
                if direction == FrameDirection.DOWNSTREAM:
                    await self._source.process_frame(frame, direction)
                else:
                    await self._sink.process_frame(frame, direction)
                
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pipeline loop error: {e}", exc_info=True)

    # --- FrameProcessor Interface Override ---

    async def process_frame(self, frame: Frame, direction: int):
        """
        When the pipeline itself is treated as a processor (nested pipelines),
        processing a frame means queuing it.
        """
        await self.queue_frame(frame, direction)

    # --- Internal Handlers ---

    async def _handle_upstream(self, frame: Frame):
        """Called when a frame reaches the very top (Source) going UP."""
        # In a standalone pipeline, this might log or drop.
        # In a nested pipeline, this would push up to the parent.
        logger.debug(f"Frame reached upstream end: {frame}")

    async def _handle_downstream(self, frame: Frame):
        """Called when a frame reaches the very bottom (Sink) going DOWN."""
        logger.debug(f"Frame reached downstream end: {frame}")
