import asyncio
import contextlib
import logging
from collections.abc import Callable, Coroutine

from app.core.frames import BackpressureFrame, Frame, SystemFrame
from app.core.processor import FrameDirection, FrameProcessor

# Configure logging
logger = logging.getLogger(__name__)

class PipelineSource(FrameProcessor):
    """
    Entry point of the pipeline.
    Acts as the source adapter, feeding frames from upstream into the pipeline.
    """
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
    """
    Exit point of the pipeline.
    Acts as the sink adapter, outputting frames from the pipeline to downstream.
    """
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
    Frame processing pipeline with backpressure management.

    Features:
    - Backpressure Management: Monitors queue size to prevent OOM.
    - Priority Queue: Ensures SystemFrames bypass traffic congestion.
    - Dropped Frame Tracking: Monitors system health under load.
    """

    def __init__(self, processors: list[FrameProcessor] | None = None, max_queue_size: int = 100):
        """
        Initialize pipeline.

        Args:
            processors: List of frame processors
            max_queue_size: Maximum queue size (default 100)
        """
        super().__init__(name="Pipeline")
        self._source = PipelineSource(self._handle_upstream)
        self._sink = PipelineSink(self._handle_downstream)

        self.processors = processors or []

        # Build the chain: Source -> [Processors] -> Sink
        self._processors = [self._source, *self.processors, self._sink]
        self._link_processors()

        # Priority Queue with max size (prevents buffer overflow)
        self._queue: asyncio.PriorityQueue[tuple[int, int, Frame, int]] = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.max_queue_size = max_queue_size
        self._running = False
        self._task = None
        self._counter = 0  # Ensures stable ordering for equal priorities

        # Backpressure tracking
        self._backpressure_warning_sent = False
        self._dropped_frames_count = 0

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
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        for p in self._processors:
            await p.cleanup()
        logger.info("Pipeline stopped.")

    async def queue_frame(self, frame: Frame, direction: int = FrameDirection.DOWNSTREAM):
        """
        Add a frame to the processing queue.

        Handles backpressure by checking queue capacity:
        - Emits WARNING signal at 80% capacity.
        - Emits CRITICAL signal when full.
        - SystemFrames have higher priority (1) than DataFrame/ControlFrame (2).
        """
        priority = 1 if isinstance(frame, SystemFrame) else 2
        self._counter += 1

        # Check queue capacity
        queue_size = self._queue.qsize()
        capacity_percent = (queue_size / self.max_queue_size) * 100 if self.max_queue_size > 0 else 0

        # Emit warning at 80% capacity
        if capacity_percent >= 80 and not self._backpressure_warning_sent:
            logger.warning(
                f"[Pipeline] Backpressure WARNING: Queue {capacity_percent:.0f}% full "
                f"({queue_size}/{self.max_queue_size})"
            )
            self._backpressure_warning_sent = True

            # Emit BackpressureFrame to notify processors
            await self._inject_critical_frame(
                BackpressureFrame(
                    queue_size=queue_size,
                    max_size=self.max_queue_size,
                    severity="warning"
                ),
                direction
            )

        # Reset warning flag when queue drains below 50%
        if capacity_percent < 50:
            self._backpressure_warning_sent = False

        # Try to add frame to queue (Non-blocking)
        try:
            self._queue.put_nowait((priority, self._counter, frame, direction))
        except asyncio.QueueFull:
            # Queue full - emit critical backpressure
            logger.error(
                f"[Pipeline] Backpressure CRITICAL: Queue FULL "
                f"({self.max_queue_size}/{self.max_queue_size}). Dropping frame: {frame.name}"
            )
            self._dropped_frames_count += 1

            # Emit critical BackpressureFrame (Attempt injection)
            await self._inject_critical_frame(
                BackpressureFrame(
                    queue_size=self.max_queue_size,
                    max_size=self.max_queue_size,
                    severity="critical"
                ),
                direction
            )

    async def _inject_critical_frame(self, frame: Frame, direction: int, force: bool = False):
        """Helper to inject high-priority system frames."""
        # Critical frames always get highest priority (0)
        priority = 0
        self._counter += 1

        try:
            # Always attempt valid insertion.
            # Note: Even critical frames can fail if queue is absolutely 100% full
            # and locked, but priority queue usually allows insertion unless hard limit.
            self._queue.put_nowait((priority, self._counter, frame, direction))
        except asyncio.QueueFull:
            logger.critical("[Pipeline] CRITICAL FAILURE: Cannot inject critical frame. Queue totally blocked.")

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
                # Prevent tight loop in case of persistent error
                await asyncio.sleep(0.1)

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
        # Log flow for debug but keep clean
        logger.debug(f"Frame reached upstream end: {frame.name}")

    async def _handle_downstream(self, frame: Frame):
        """Called when a frame reaches the very bottom (Sink) going DOWN."""
        logger.debug(f"Frame reached downstream end: {frame.name}")
