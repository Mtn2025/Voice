import logging
import asyncio
from typing import Any, Optional

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, AudioFrame, CancelFrame
from app.services.base import TTSProvider
from app.utils.ssml_builder import build_azure_ssml

logger = logging.getLogger(__name__)

class TTSProcessor(FrameProcessor):
    """
    Consumes TextFrames, calls TTS Provider, produces AudioFrames.
    Supports cancellation via CancelFrame.
    """
    def __init__(self, provider: TTSProvider, config: Any):
        super().__init__(name="TTSProcessor")
        self.provider = provider
        self.config = config
        self.synthesizer = None # Initialize using provider if needed
        self._current_task: Optional[asyncio.Task] = None

    async def initialize(self):
         # Call provider specific init
         if self.provider:
             self.synthesizer = self.provider.create_synthesizer(
                 voice_name=getattr(self.config, 'voice_name', 'en-US-JennyNeural'),
                 audio_mode=getattr(self.config, 'client_type', 'twilio')
             )

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
            # Build SSML
            ssml = build_azure_ssml(
                voice_name=getattr(self.config, 'voice_name', 'en-US-JennyNeural'),
                text=text,
                rate=getattr(self.config, 'voice_speed', 1.0),
                pitch=getattr(self.config, 'voice_pitch', 0),
                volume=getattr(self.config, 'voice_volume', 100),
                style=getattr(self.config, 'voice_style', None),
                style_degree=getattr(self.config, 'voice_style_degree', 1.0)
            )

            if not self.synthesizer:
                await self.initialize() # Lazy Init
                if not self.synthesizer:
                     logger.warning("TTS Synthesizer failed to init.")
                     return

            audio_data = await self.provider.synthesize_ssml(self.synthesizer, ssml)
            
            if audio_data:
                logger.info(f"🗣️ [TTS] Received Audio Data: {len(audio_data)} bytes")
                
                # CRITICAL: Do NOT chunk here. 
                # 1. For Browser: We need the full blob to avoid overwhelming the JS AudioContext scheduler with 5ms clips.
                # 2. For Telephony: The Orchestrator.send_audio_chunked method ALREADY re-chunks to 160 bytes.
                # Sending the full blob preserves efficiency and correctness.
                
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
