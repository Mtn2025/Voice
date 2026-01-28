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
        client_type = getattr(self.config, 'client_type', 'twilio')
        stt_lang = getattr(self.config, 'stt_language', 'es-MX')
        
        try:
             self.recognizer = self.provider.create_recognizer(
                language=stt_lang,
                audio_mode=client_type
            )
             
             # Register unified callback via Wrapper's subscribe
             if hasattr(self.recognizer, 'subscribe'):
                 self.recognizer.subscribe(self._on_stt_event)
             else:
                 # Fallback for native object (unlikely if provider is AzureProvider)
                 # But just in case
                 if hasattr(self.recognizer, 'recognized'):
                    self.recognizer.recognized.connect(self._on_recognized_native)
                    self.recognizer.canceled.connect(self._on_canceled_native)
             
             # Start recognition
             if hasattr(self.recognizer, 'start_continuous_recognition_async'):
                self.recognizer.start_continuous_recognition_async().get()
             
             logger.info("STTProcessor initialized and recognition started.")
             
        except Exception as e:
            logger.error(f"Failed to initialize STTProcessor: {e}")
            raise

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                # Write to Azure Stream
                if self.recognizer and hasattr(self.recognizer, 'write'):
                    # push_stream.write() expects bytes
                    self.recognizer.write(frame.data)
                
                # CRITICAL FIX: Propagate audio to next processor (VAD)
                await self.push_frame(frame, direction)
            else:
                # Pass through other frames
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def cleanup(self):
        if self.recognizer:
            try:
                if hasattr(self.recognizer, 'stop_continuous_recognition_async'):
                     self.recognizer.stop_continuous_recognition_async().get()
            except Exception:
                pass
        
    # --- callbacks ---
    
    def _on_stt_event(self, evt: STTEvent):
        """
        Unified callback from Provider Wrapper.
        evt is app.services.base.STTEvent
        """
        if evt.reason == STTResultReason.RECOGNIZED_SPEECH:
            text = evt.text
            if text:
                # --- AUDIT FIX: Filtering Logic ---
                
                # 1. Blacklist (Hallucinations)
                blacklist_str = getattr(self.config, 'hallucination_blacklist', '') or ''
                blacklist = [x.strip() for x in blacklist_str.split(',') if x.strip()]
                if any(bad_phrase in text for bad_phrase in blacklist):
                    logger.warning(f"🔇 [STT] Ignored (Blacklist): {text}")
                    return

                # 2. Min Characters (Interruption Threshold)
                # Note: UI says 'interruptWords' but maps to 'input_min_characters' usually. 
                # Let's use 'input_min_characters' from DB.
                min_chars = getattr(self.config, 'input_min_characters', 2)
                if len(text) < min_chars:
                    logger.warning(f"🔇 [STT] Ignored (Too Short < {min_chars}): {text}")
                    return

                logger.info(f"🎤 [STT] Recognized: {text}")
                asyncio.run_coroutine_threadsafe(
                    self.push_frame(TextFrame(text=text, is_final=True)), 
                    self.loop
                )
        elif evt.reason == STTResultReason.CANCELED:
            logger.warning(f"STT Canceled. Details: {evt.error_details}")
            
    # Legacy/Native callbacks (Fallback only)
    def _on_recognized_native(self, evt):
        # ... logic for native azure event if needed ...
        pass
        
    def _on_canceled_native(self, evt):
        pass
