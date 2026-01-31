"""
Adaptador Azure STT Adapter - Implementación de STTPort.

Wrappea la lógica de Azure Speech SDK manteniendo separación arquitectónica.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import azure.cognitiveservices.speech as speechsdk
from circuitbreaker import circuit
from groq import AsyncGroq

from app.core.config import settings
from app.core.decorators import track_latency
from app.domain.ports import (
    STTConfig,
    STTEvent,
    STTException,
    STTPort,
    STTRecognizer,
    STTResultReason,
)

logger = logging.getLogger(__name__)


class AzureRecognizerWrapper:
    """Wrapper para eventos de Azure SDK."""
    def __init__(self, recognizer, push_stream):
        self._recognizer = recognizer
        self._push_stream = push_stream
        self._callback = None

        # Wire events
        self._recognizer.recognized.connect(self._on_event)
        self._recognizer.recognizing.connect(self._on_event)
        self._recognizer.canceled.connect(self._on_canceled)

    def subscribe(self, callback):
        self._callback = callback

    def _on_event(self, evt):
        if not self._callback:
            return

        reason = STTResultReason.UNKNOWN
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            reason = STTResultReason.RECOGNIZED_SPEECH
        elif evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
            reason = STTResultReason.RECOGNIZING_SPEECH
        else:
            return

        text = evt.result.text
        if not text:
            return

        event = STTEvent(
            reason=reason,
            text=text,
            duration=getattr(evt.result, 'duration', 0.0)
        )
        self._callback(event)

    def _on_canceled(self, evt):
        if not self._callback:
            return
        details = ""
        if hasattr(evt, 'result') and hasattr(evt.result, 'cancellation_details'):
             details = evt.result.cancellation_details.error_details

        event = STTEvent(
            reason=STTResultReason.CANCELED,
            text="",
            error_details=details
        )
        self._callback(event)

    def start_continuous_recognition_async(self):
        return self._recognizer.start_continuous_recognition_async()

    def stop_continuous_recognition_async(self):
        return self._recognizer.stop_continuous_recognition_async()

    def write(self, data):
        self._push_stream.write(data)


class AzureSTTRecognizerAdapter(STTRecognizer):
    """
    Wrapper sobre AzureRecognizerWrapper que implementa STTRecognizer.
    """

    def __init__(self, azure_recognizer: AzureRecognizerWrapper):
        self._azure_recognizer = azure_recognizer

    def subscribe(self, callback: Callable[[STTEvent], None]):
        """Suscribe callback para eventos STT."""
        self._azure_recognizer.subscribe(callback)

    async def start_continuous_recognition(self):
        """Inicia reconocimiento continuo."""
        future = self._azure_recognizer.start_continuous_recognition_async()
        # Azure returns a future, wait for it
        future.get()

    def start_continuous_recognition_async(self):
        """
        Legacy support for STTProcessor calling this directly.
        Returns the Azure Future object.
        """
        return self._azure_recognizer.start_continuous_recognition_async()

    async def stop_continuous_recognition(self):
        """Detiene reconocimiento continuo."""
        future = self._azure_recognizer.stop_continuous_recognition_async()
        future.get()

    def stop_continuous_recognition_async(self):
        """
        Legacy support for STTProcessor calling this directly.
        Returns the Azure Future object.
        """
        return self._azure_recognizer.stop_continuous_recognition_async()

    def write(self, audio_data: bytes):
        """Escribe datos de audio al stream."""
        self._azure_recognizer.write(audio_data)


class AzureSTTAdapter(STTPort):
    """
    Adaptador para Azure STT que implementa STTPort.
    """

    def __init__(self, config: Any | None = None):
        """
        Args:
            config: Clean config object (provided by factory) or None.
        """
        self.api_key = config.api_key if config else settings.AZURE_SPEECH_KEY
        self.region = config.region if config else settings.AZURE_SPEECH_REGION

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.api_key,
            region=self.region
        )

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=STTException)
    def create_recognizer(
        self,
        config: STTConfig,
        on_interruption_callback: Callable | None = None,
        event_loop: Any | None = None
    ) -> STTRecognizer:
        """
        Crea recognizer configurado según STTConfig.
        """
        try:
            self.speech_config.speech_recognition_language = config.language

            # Apply Timeouts
            self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, str(config.initial_silence_ms))
            self.speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, str(config.segmentation_silence_ms))

            if config.audio_mode == "browser":
                 format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
            else:
                 # Manual Decode Mode (Twilio/Telnyx) -> 8000Hz
                 format = speechsdk.audio.AudioStreamFormat(samples_per_second=8000, bits_per_sample=16, channels=1)

            push_stream = speechsdk.audio.PushAudioInputStream(stream_format=format)
            audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

            azure_native_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            # Barge-in Logic (Legacy Support)
            if on_interruption_callback and event_loop:
                def recognizing_cb(evt):
                    if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
                        text = evt.result.text
                        if on_interruption_callback:
                             event_loop.call_soon_threadsafe(
                                lambda: asyncio.create_task(on_interruption_callback(text))
                            )
                azure_native_recognizer.recognizing.connect(recognizing_cb)

            wrapper = AzureRecognizerWrapper(azure_native_recognizer, push_stream)

            # Wrap in our hexagonal adapter
            return AzureSTTRecognizerAdapter(wrapper)

        except Exception as e:
            logger.error(f"Azure STT recognizer creation failed: {e}")
            if "auth" in str(e).lower() or "key" in str(e).lower():
                raise STTException("Azure STT authentication failed", retryable=False, provider="azure", original_error=e) from e
            raise STTException(f"Could not create recognizer: {e!s}", retryable=True, provider="azure", original_error=e) from e

    @track_latency("azure_stt")
    async def transcribe_audio(self, audio_bytes: bytes, language: str = "es") -> str:
        """
        Transcribe audio completo usando Groq Whisper (Fallback/Utility).
        Uses simple Groq implementation directly to avoid circular deps.
        """
        try:
            import io
            client = AsyncGroq(api_key=settings.GROQ_API_KEY)

            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"

            transcription = await client.audio.transcriptions.create(
                file=(audio_file.name, audio_file.read()),
                model="whisper-large-v3",
                response_format="json",
                language=language,
                temperature=0.0
            )
            return transcription.text

        except Exception as e:
            logger.warning(f"Audio transcription failed: {e}")
            retryable = "timeout" in str(e).lower() or "connection" in str(e).lower()
            raise STTException(
                f"Audio transcription failed: {e!s}",
                retryable=retryable,
                provider="groq",
                original_error=e
            ) from e

    async def close(self):
        """Limpia."""
        pass
