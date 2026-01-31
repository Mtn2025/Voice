import asyncio
import contextlib
import json
import logging
from typing import Any

from app.core.frames import AudioFrame, CancelFrame, Frame, TextFrame
from app.core.processor import FrameDirection, FrameProcessor
from app.domain.ports.stt_port import STTConfig
from app.services.base import STTEvent, STTProvider, STTResultReason

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
        self.control_channel = control_channel
        self.push_stream = None # Azure PushAudioInputStream
        self.recognizer = None

    async def initialize(self):
        """
        Initialize Azure Recoginzer and PushStream.
        """
        # Get profile configuration (type-safe, centralized)
        client_type = getattr(self.config, 'client_type', 'twilio')
        profile = self.config.get_profile(client_type)

        stt_config = STTConfig(
            language=profile.stt_language or 'es-MX',
            audio_mode=client_type,

            # Basic
            initial_silence_ms=profile.initial_silence_timeout_ms or 5000,

            # Phase III: Advanced STT Controls (not yet in ProfileConfig - using defaults)
            model='default',  # TODO: Add to ProfileConfigSchema
            keywords=None,
            silence_timeout=500,
            utterance_end_strategy='default',

            # Formatting (defaults until added to ProfileConfig)
            punctuation=True,
            profanity_filter=True,
            smart_formatting=True,

            # Advanced (defaults until added to ProfileConfig)
            diarization=False,
            multilingual=False
        )

        try:
             self.recognizer = self.provider.create_recognizer(
                config=stt_config
            )

             # Register unified callback via Wrapper's subscribe
             # We assume the provider implements the uniform interface
             self.recognizer.subscribe(self._on_stt_event)

             # Start recognition
             # Note: wrapping in executor to avoid blocking loop if provider implementation is synchronous or uses .get()
             await self.loop.run_in_executor(None, self.recognizer.start_continuous_recognition_async().get)

             logger.info("STTProcessor initialized and recognition started.")

        except Exception as e:
            logger.error(f"Failed to initialize STTProcessor: {e}")
            raise

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                # Write to Azure Stream
                if self.recognizer and hasattr(self.recognizer, 'write'):
                    self.recognizer.write(frame.data)

                # Propagate audio to next processor (VAD)
                await self.push_frame(frame, direction)
            else:
                # Pass through other frames
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def cleanup(self):
        if self.recognizer:
            # Non-blocking cleanup attempt
            with contextlib.suppress(Exception):
                await self.loop.run_in_executor(None, self.recognizer.stop_continuous_recognition_async().get)

    # --- callbacks ---

    def _on_stt_event(self, evt: STTEvent):
        """
        Unified callback from Provider Wrapper.
        evt is app.services.base.STTEvent
        """
        if evt.reason == STTResultReason.RECOGNIZED_SPEECH:
            text = evt.text
            if text:
                # --- Filtering Logic ---

                # 1. Blacklist (Hallucinations)
                blacklist_str = getattr(self.config, 'hallucination_blacklist', '') or ''
                blacklist = [x.strip() for x in blacklist_str.split(',') if x.strip()]
                if any(bad_phrase in text for bad_phrase in blacklist):
                    logger.warning(f"🔇 [STT] Ignored (Blacklist): {text}")
                    return

                # 2. Min Characters (Interruption Threshold)
                val = getattr(self.config, 'input_min_characters', 2)
                min_chars = val if val is not None else 2
                if len(text) < min_chars:
                    logger.warning(f"🔇 [STT] Ignored (Too Short < {min_chars}): {text}")
                    return

                # 3. Interruption Phrases (Force Stop)
                # Use profile configuration for type-safe access
                client_type = getattr(self.config, 'client_type', 'twilio')
                profile = self.config.get_profile(client_type)

                phrases_json = profile.interruption_phrases

                if phrases_json:
                    text_lower = text.lower()
                    try:
                        if isinstance(phrases_json, str):
                            phrases = json.loads(phrases_json)
                        else:
                            phrases = phrases_json

                        if isinstance(phrases, list):
                            for phrase in phrases:
                                if phrase.lower() in text_lower:
                                    logger.info(f"⚡ [STT] Interruption Phrase Detected: '{phrase}' - FORCING STOP")

                                    # Out-of-Band Signal (Priority)
                                    if self.control_channel:
                                        asyncio.run_coroutine_threadsafe(
                                            self.control_channel.send_interrupt(text=f"Keyword: {phrase}"),
                                            self.loop
                                        )

                                    # In-Band Signal (Fallback)
                                    asyncio.run_coroutine_threadsafe(
                                        self.push_frame(CancelFrame()),
                                        self.loop
                                    )
                                    break
                    except Exception as e:
                        logger.warning(f"Failed to parse interruption_phrases: {e}")

                logger.info(f"🎤 [STT] Recognized: {text}")

                # [TRACING] Log STT Event
                logger.debug(f"👂 [STT_EVENT] Text: '{text}' | Confidence: High | Trace: {getattr(self.config, 'stream_id', 'unknown')}")

                asyncio.run_coroutine_threadsafe(
                    self.push_frame(TextFrame(text=text, is_final=True)),
                    self.loop
                )
        elif evt.reason == STTResultReason.CANCELED:
            logger.warning(f"STT Canceled. Details: {evt.error_details}")
