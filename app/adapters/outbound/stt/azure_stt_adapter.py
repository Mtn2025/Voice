"""
Adaptador Azure STT Adapter - Implementación de STTPort.

Wrappea la lógica de Azure Speech SDK manteniendo separación arquitectónica.
"""

import logging
import time  # ✅ Module 5: For latency tracking
from typing import AsyncIterator, Optional, Callable, Any
import azure.cognitiveservices.speech as speechsdk
from circuitbreaker import circuit  # Professional error handling
from app.domain.ports import (
    STTPort,
    STTRecognizer,
    STTConfig,
    STTEvent,
    STTResultReason,
    STTException
)
from app.providers.azure import AzureProvider, AzureRecognizerWrapper
from app.core.decorators import track_latency  # ✅ P3: Metrics TTFB


logger = logging.getLogger(__name__)


class AzureSTTRecognizerAdapter(STTRecognizer):
    """
    Wrapper sobre AzureRecognizerWrapper que implementa STTRecognizer.
    
    Proporciona interface hexagonal limpia sobre Azure SDK.
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
    
    async def stop_continuous_recognition(self):
        """Detiene reconocimiento continuo."""
        future = self._azure_recognizer.stop_continuous_recognition_async()
        future.get()
    
    def write(self, audio_data: bytes):
        """Escribe datos de audio al stream."""
        self._azure_recognizer.write(audio_data)


class AzureSTTAdapter(STTPort):
    """
    Adaptador para Azure STT que implementa STTPort.
    
    Mantiene toda la lógica de configuración de formatos
    (8khz/16khz, mulaw/alaw/pcm) del provider existente.
    
    ✅ Hexagonal: Recibe config object (no settings directos)
    """
    
    def __init__(self, config: 'STTProviderConfig' = None):
        """
        Args:
            config: Clean config object (provided by factory)
                    If None, reads from settings (backwards compatible)
        """
        from app.core.config import settings
        
        if config:
            # ✅ Clean injection from factory
            self.azure_provider = AzureProvider(
                api_key=config.api_key,
                region=config.region
            )
        else:
            # Backwards compatible (legacy)
            self.azure_provider = AzureProvider()
    
    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=STTException)
    def create_recognizer(
        self,
        config: STTConfig,
        on_interruption_callback: Optional[Callable] = None,
        event_loop: Optional[Any] = None
    ) -> STTRecognizer:
        """
        Crea recognizer configurado según STTConfig.
        
        Translates Azure SDK exceptions into domain STTException.
        """
        try:
            # Use existing Azure provider method
            azure_recognizer = self.azure_provider.create_recognizer(
                language=config.language,
                audio_mode=config.audio_mode,
                on_interruption_callback=on_interruption_callback,
                event_loop=event_loop,
                initial_silence_ms=config.initial_silence_ms,
                segmentation_silence_ms=config.segmentation_silence_ms
            )
            
            # Wrap it in our hexagonal adapter
            return AzureSTTRecognizerAdapter(azure_recognizer)
        
        # HEXAGONAL: Translate infrastructure exceptions to domain
        except STTException:
            raise
        
        except Exception as e:
            logger.error(f"Azure STT recognizer creation failed: {e}")
            # Check if it's authentication or network issue
            if "auth" in str(e).lower() or "key" in str(e).lower():
                raise STTException(
                    "Azure STT authentication failed",
                    retryable=False,
                    provider="azure",
                    original_error=e
                ) from e
            else:
                raise STTException(
                    f"Could not create recognizer: {str(e)}",
                    retryable=True,
                    provider="azure",
                    original_error=e
                ) from e
    
    @track_latency("azure_stt")  # ✅ P3: Track TTFB metrics
    async def transcribe_audio(self, audio_bytes: bytes, language: str = "es") -> str:
        """
        Transcribe audio completo (no streaming).
        
        Uses Groq Whisper from provider if available.
        Translates exceptions to domain STTException.
        """
        try:
            # AzureProvider has transcribe_audio method via Groq
            from app.providers.groq import GroqProvider
            groq = GroqProvider()
            return await groq.transcribe_audio(audio_bytes, language)
        
        except STTException:
            raise
        
        except Exception as e:
            logger.warning(f"Audio transcription failed: {e}")
            # Determine if retryable
            retryable = "timeout" in str(e).lower() or "connection" in str(e).lower()
            raise STTException(
                f"Audio transcription failed: {str(e)}",
                retryable=retryable,
                provider="groq",  # Using Groq Whisper
                original_error=e
            ) from e
    
    async def close(self):
        """Limpia recursos de Azure provider."""
        await self.azure_provider.close()
