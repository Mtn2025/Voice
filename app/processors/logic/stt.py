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
    def __init__(self, provider: STTProvider, config: Any, loop: asyncio.AbstractEventLoop, control_channel=None):
        super().__init__(name="STTProcessor")
        self.provider = provider
        self.config = config
        self.loop = loop
        self.control_channel = control_channel # ✅ Module 13: Out-of-Band Signaling
        self.push_stream = None # Azure PushAudioInputStream
        self.recognizer = None

    async def initialize(self):
        """
        Initialize Azure Recoginzer and PushStream.
        """
        from app.domain.ports.stt_port import STTConfig # Import here to avoid circulars if any
        
        # 1. Determine Suffix based on Client Type
        client_type = getattr(self.config, 'client_type', 'twilio')
        suffix = ""
        if client_type == "twilio":
            suffix = "_phone"
        elif client_type == "telnyx":
            suffix = "_telnyx"
            
        def get_conf(base_name, default=None):
            """Helper to get config with profile fallback."""
            # 1. Try suffixed version (e.g., stt_model_phone)
            val = getattr(self.config, f"{base_name}{suffix}", None)
            if val is not None:
                return val
            # 2. Fallback to base (e.g., stt_model)
            return getattr(self.config, base_name, default)
        
        stt_config = STTConfig(
            language=get_conf('stt_language', 'es-MX'),
            audio_mode=client_type,
            
            # Basic
            initial_silence_ms=get_conf('initial_silence_timeout_ms', 5000), # Note: model has suffix field
            
            # Phase III: Advanced STT Controls
            model=get_conf('stt_model', 'default'),
            keywords=get_conf('stt_keywords', None),
            silence_timeout=get_conf('stt_silence_timeout', 500),
            utterance_end_strategy=get_conf('stt_utterance_end_strategy', 'default'),
            
            # Formatting
            punctuation=get_conf('stt_punctuation', True),
            profanity_filter=get_conf('stt_profanity_filter', True),
            smart_formatting=get_conf('stt_smart_formatting', True),
            
            # Advanced
            diarization=get_conf('stt_diarization', False),
            multilingual=get_conf('stt_multilingual', False)
        )
        
        try:
             self.recognizer = self.provider.create_recognizer(
                config=stt_config
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
                val = getattr(self.config, 'input_min_characters', 2)
                min_chars = val if val is not None else 2
                if len(text) < min_chars:
                    logger.warning(f"🔇 [STT] Ignored (Too Short < {min_chars}): {text}")
                    return

                # 3. Interruption Phrases (Phase IV - Force Stop)
                # Dynamic Config Resolution
                client_type = getattr(self.config, 'client_type', 'twilio')
                suffix = "_phone" if client_type == "twilio" else ("_telnyx" if client_type == "telnyx" else "")
                
                phrases_json = getattr(self.config, f"interruption_phrases{suffix}", None) or getattr(self.config, "interruption_phrases", None)
                
                if phrases_json:
                    # Check if any phrase is in text (case insensitive)
                    text_lower = text.lower()
                    import json
                    try:
                        if isinstance(phrases_json, str):
                            phrases = json.loads(phrases_json)
                        else:
                            phrases = phrases_json # Already list/dict
                            
                        if isinstance(phrases, list):
                            for phrase in phrases:
                                if phrase.lower() in text_lower:
                                    logger.info(f"⚡ [STT] Interruption Phrase Detected: '{phrase}' - FORCING STOP")
                                    
                                    # ✅ Module 13: Out-of-Band Signal (Priority)
                                    if self.control_channel:
                                        # Use run_coroutine_threadsafe because callback is thread-safe wrapper
                                        future = asyncio.run_coroutine_threadsafe(
                                            self.control_channel.send_interrupt(text=f"Keyword: {phrase}"),
                                            self.loop
                                        )
                                    
                                    # In-Band Signal (Legacy Fallback)
                                    asyncio.run_coroutine_threadsafe(
                                        self.push_frame(CancelFrame()), 
                                        self.loop
                                    )
                                    break
                    except Exception as e:
                        logger.warning(f"Failed to parse interruption_phrases: {e}")

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
