import logging
import asyncio
from typing import Any, Optional

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, AudioFrame, TextFrame
from app.services.base import STTProvider, STTEvent, STTResultReason

logger = logging.getLogger(__name__)

class STTProcessor(FrameProcessor):
    """
    Consumes AudioFrames, writes to Azure PushStream.
    Listens to Azure Events, produces TextFrames.
    """
    def __init__(self, provider: STTProvider, config: Any, loop: asyncio.AbstractEventLoop):
        super().__init__(name="STTProcessor")
        self.provider = provider
        self.config = config
        self.loop = loop
        self.push_stream = None # Azure PushAudioInputStream
        self.recognizer = None

    async def initialize(self):
        """
        Initialize Azure Recoginzer and PushStream.
        """
        # We need to setup the recognizer similar to VoiceOrchestrator._setup_stt
        # But here we might rely on the Orchestrator to pass the initialized objects?
        # Or better, we encapsulate the setup here.
        
        # NOTE: provider.create_recognizer returns (recognizer, push_stream)
        # We assume the provider has this method (as seen in Orchestrator)
        
        client_type = getattr(self.config, 'client_type', 'twilio')
        stt_lang = getattr(self.config, 'stt_language', 'es-MX')
        
        try:
             self.recognizer, self.push_stream = self.provider.create_recognizer(
                language=stt_lang,
                client_type=client_type
            )
             
             # Register callbacks
             # Note: These are synchronous callbacks from Azure SDK threads
             self.recognizer.recognized.connect(self._on_recognized)
             # self.recognizer.recognizing.connect(self._on_recognizing) # If we want interim results
             self.recognizer.canceled.connect(self._on_canceled)
             
             # Start recognition
             self.recognizer.start_continuous_recognition_async().get()
             logger.info("STTProcessor initialized and recognition started.")
             
        except Exception as e:
            logger.error(f"Failed to initialize STTProcessor: {e}")
            raise

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                # Write to Azure Stream
                if self.push_stream:
                    # push_stream.write() expects bytes
                    self.push_stream.write(frame.data)
            else:
                # Pass through other frames
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def cleanup(self):
        if self.recognizer:
            try:
                self.recognizer.stop_continuous_recognition_async().get()
            except Exception:
                pass
        
    # --- callbacks ---
    
    def _on_recognized(self, evt):
        """
        Azure SDK callback (Threaded).
        """
        if evt.result.reason == STTResultReason.RecognizedSpeech:
            text = evt.result.text
            if text:
                logger.info(f"🎤 [STT] Recognized: {text}")
                # We need to create a TextFrame and push it.
                # Since we are in a thread, we must schedule it in the loop.
                asyncio.run_coroutine_threadsafe(
                    self.push_frame(TextFrame(text=text, is_final=True)), 
                    self.loop
                )

    def _on_canceled(self, evt):
        logger.warning(f"STT Canceled: {evt}")
