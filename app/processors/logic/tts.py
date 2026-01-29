import logging
import asyncio
from typing import Any, Optional

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, AudioFrame, CancelFrame
from app.domain.ports import TTSPort, TTSRequest  # ✅ P1: Hexagonal (NO legacy TTSProvider)
from app.utils.ssml_builder import build_azure_ssml

logger = logging.getLogger(__name__)

class TTSProcessor(FrameProcessor):
    """
    Consumes TextFrames, calls TTS Port (Hexagonal), produces AudioFrames.
    Supports cancellation via CancelFrame.
    
    ✅ P1: Backpressure detection - monitors queue size and signals adapters
    """
    def __init__(self, tts_port: TTSPort, config: Any):
        super().__init__(name="TTSProcessor")
        self.tts_port = tts_port  # ✅ P1: TTSPort (hexagonal)
        self.config = config
        self._current_task: Optional[asyncio.Task] = None
        
        # ✅ P1: Backpressure threshold (queue depth)
        self.backpressure_threshold = getattr(config, 'tts_backpressure_threshold', 3)
    
    # NO initialize needed - TTSPort is ready to use

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, TextFrame):
                # Optionally cancel previous TTS if new text comes? 
                # Depends on strategy. Usually TTS queues up.
                # But for interruption, we definitely cancel.
                # For now, let's treat TextFrames as sequential.
                # But we should spawn a task so we don't block the pipeline loop.
                # Wait, if we spawn a task for *each* text frame, audio might arrive out of order?
                # No, if we use a queue internally or if we await the task *in order*?
                # Pipeline Loop is serial. If we spawn, we lose order unless we manage it.
                # BUT, `LLMProcessor` pushes TextFrames sequentially.
                # If `TTSProcessor` spawns tasks immediately, short tasks might finish before long ones.
                # Best practice: Use an internal queue and a worker task?
                # Or just await in `process_frame` but verify Cancellation?
                # But awaiting blocks `process_frame` from seeing `CancelFrame`.
                
                # SOLUTION: Spawn task, but chain them? 
                # Or, simpler: Check for `CancelFrame` *during* synthesis is hard if `await` blocks.
                # Let's use a Task that processes an internal Queue?
                
                # For this iteration, let's spawn a task and hope for order, or trust that asyncio queues maintain some order.
                # Actually, standard asyncio tasks don't guarantee completion order.
                # A safer bet for TSS is to use an internal Queue and a consumer loop.
                
                await self._queue_text(frame.text)
                
            elif isinstance(frame, CancelFrame):
                logger.info("🛑 [TTS] Received CancelFrame. clearing queue.")
                await self._clear_queue()
                await self.push_frame(frame, direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    # --- Internal Queue Management ---
    
    async def _queue_text(self, text: str):
        # We need to initialize the worker if not running
        if not hasattr(self, '_tts_queue'):
            self._tts_queue = asyncio.Queue()
            self._worker_task = asyncio.create_task(self._worker())
            
        await self._tts_queue.put(text)

    async def _worker(self):
        while True:
            try:
                text = await self._tts_queue.get()
                await self._synthesize(text)
                self._tts_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"TTS Worker Error: {e}")

    async def _clear_queue(self):
        # Empty the queue
        if hasattr(self, '_tts_queue'):
            while not self._tts_queue.empty():
                try:
                    self._tts_queue.get_nowait()
                    self._tts_queue.task_done()
                except:
                    pass
        # Cancel current synthesis? 
        # If `_synthesize` check for cancellation flag?
        # We can restart the worker.
        if hasattr(self, '_worker_task'):
            self._worker_task.cancel()
            self._worker_task = asyncio.create_task(self._worker())

    async def _synthesize(self, text: str):
        if not text:
            return

        logger.info(f"🗣️ [TTS] Synthesizing: {text}")
        
        try:
            # ✅ P1: Detect backpressure (queue depth)
            backpressure_detected = False
            if hasattr(self, '_tts_queue'):
                queue_depth = self._tts_queue.qsize()
                backpressure_detected = queue_depth >= self.backpressure_threshold
                
                if backpressure_detected:
                    logger.warning(
                        f"⚠️ [TTS] Backpressure detected: queue_depth={queue_depth} "
                        f">= threshold={self.backpressure_threshold}"
                    )
            
            # ✅ P1: Create TTSRequest with backpressure flag
            request = TTSRequest(
                text=text,
                voice_id=getattr(self.config, 'voice_name', 'en-US-JennyNeural'),
                language=getattr(self.config, 'language', 'es-MX'),
                speed=getattr(self.config, 'voice_speed', 1.0),
                pitch=getattr(self.config, 'voice_pitch', 0.0),
                volume=getattr(self.config, 'voice_volume', 100.0),
                style=getattr(self.config, 'voice_style', None),
                backpressure_detected=backpressure_detected  # ✅ P1: Signal to adapter
            )
            
            # ✅ P1: Call TTSPort (hexagonal)
            audio_data = b""
            async for audio_chunk in self.tts_port.synthesize_stream(request):
                audio_data += audio_chunk
            
            if audio_data:
                logger.info(f"🗣️ [TTS] Received Audio Data: {len(audio_data)} bytes")
                
                # Determine metadata sample rate
                sr = 16000 if getattr(self.config, 'client_type', 'twilio') == 'browser' else 8000
                
                await self.push_frame(AudioFrame(data=audio_data, sample_rate=sr, channels=1))
            else:
                logger.warning("🗣️ [TTS] Audio Data is empty/None!")
                    
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    async def stop(self):
        """Stops the TTS processor and cleans up tasks."""
        if hasattr(self, '_worker_task') and self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        await super().stop()
