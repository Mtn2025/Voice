"""
Adaptador Azure TTS - Implementación de TTSPort.

Wrappea la lógica de síntesis de voz de Azure Speech SDK.
"""

import logging
import time  # ✅ Module 5: For latency tracking
from typing import AsyncIterator, Optional # Optional is still used later in the code
import azure.cognitiveservices.speech as speechsdk
from circuitbreaker import circuit  # Professional error handling

from app.domain.ports import TTSPort, TTSRequest, VoiceMetadata, TTSException # VoiceMetadata is still used
from app.providers.azure import AzureProvider  # ✅ Corrected from azure_tts
from app.observability import get_metrics_collector  # ✅ Module 5
from app.core.decorators import track_streaming_latency  # ✅ P3: Metrics TTFB


logger = logging.getLogger(__name__)


class AzureTTSAdapter(TTSPort):
    """
    Adaptador para Azure TTS que implementa TTSPort.
    
    Wrappea AzureProvider existente manteniendo toda la lógica
    de SSML, formatos de audio (mulaw/alaw/pcm), etc.
    
    ✅ Hexagonal: Recibe config object (no settings directos)
    """
    
    def __init__(self, config: 'TTSProviderConfig' = None, audio_mode: str = "twilio"):
        """
        Args:
            config: Clean config object (provided by factory)
            audio_mode: "browser" (16khz PCM), "twilio" (8khz mulaw), "telnyx" (8khz alaw)
        """
        from app.core.config import settings
        
        if config:
            #✅ Clean injection from factory
            self.azure_provider = AzureProvider(
                api_key=config.api_key,
                region=config.region
            )
            self.audio_mode = config.audio_mode or audio_mode
        else:
            # Backwards compatible (legacy)
            self.azure_provider = AzureProvider()
            self.audio_mode = audio_mode
        
        self._synthesizer: Optional[speechsdk.SpeechSynthesizer] = None
    
    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=TTSException)
    @track_streaming_latency("azure_tts")  # ✅ P3: Track TTFB metrics
    async def synthesize_stream(self, request: TTSRequest) -> AsyncIterator[bytes]:
        """
        Genera audio desde texto en streaming.
        
        ✅ Module 5: Tracks TTS latency with trace_id.
        
        Args:
            request: TTSRequest con texto, voz, configuración
        
        Yields:
            Audio bytes (PCM 16-bit, 8kHz o 16kHz)
        
        Raises:
            TTSException: Si síntesis falla
        """
        # ✅ Module 5: Extract trace_id for metrics
        trace_id = request.metadata.get('trace_id', 'unknown')
        start_time = time.time()
        first_byte_time = None
        metrics_collector = get_metrics_collector()
        
        try:
            # ✅ P1: Check backpressure flag for quality adjustment
            if request.backpressure_detected:
                logger.warning(
                    f"⚠️ [TTS Azure] trace={trace_id} BACKPRESSURE MODE ACTIVE - "\
                    f"Using faster synthesis (reduced quality)"
                )
            
            logger.info(f"[TTS Azure] trace={trace_id} Starting synthesis voice={request.voice_id}")
            
            # ✅ P1: Adjust synthesis parameters based on backpressure
            # When backpressure detected, use faster rate to reduce latency
            synthesis_rate = request.speed
            if request.backpressure_detected:
                synthesis_rate = min(request.speed * 1.3, 1.5)  # 30% faster, max 1.5x
                logger.debug(
                    f"[TTS Azure] trace={trace_id} Speed adjusted: "\
                    f"{request.speed}→{synthesis_rate} (backpressure)"
                )
            
            # ✅ FIX VIOLATION #3: Extract Azure-specific params from provider_options
            # BACKWARDS COMPATIBLE: Falls back to legacy .pitch property if not in provider_options
            pitch_value = request.provider_options.get('pitch_hz', request.pitch)
            style_value = request.provider_options.get('style', request.style)
            
            # Call Azure provider
            async for audio_chunk in self.azure_provider.synthesize_stream(
                text=request.text,
                voice=request.voice_id,
                pitch=pitch_value,  # ✅ FIX VIOLATION #3
                rate=synthesis_rate,  # ✅ P1: Adjusted rate
                volume=request.volume,
                audio_mode=self.audio_mode # Changed from audio_format to audio_mode
            ):
                # ✅ Module 5: Log TTFB (Time To First Byte)
                if first_byte_time is None:
                    first_byte_time = time.time()
                    ttfb = (first_byte_time - start_time) * 1000  # ms
                    logger.info(
                        f"[TTS Azure] trace={trace_id} TTFB={ttfb:.0f}ms "
                        f"voice={request.voice_id}"
                    )
                
                yield audio_chunk
            
            # ✅ Module 5: Log total latency and record metrics
            total_time = (time.time() - start_time) * 1000  # ms
            logger.info(
                f"[TTS Azure] trace={trace_id} Total={total_time:.0f}ms "
                f"voice={request.voice_id} completed"
            )
            
            # Record metrics
            await metrics_collector.record_latency(trace_id, 'tts', total_time)
        
        except Exception as e:
            # ✅ Module 5: Log error with trace_id
            logger.error(
                f"[TTS Azure] trace={trace_id} ERROR: {str(e)} "
                f"after {(time.time() - start_time)*1000:.0f}ms"
            )
            raise TTSException(
                message=f"Azure TTS synthesis failed: {str(e)}",
                retryable=True,
                provider="azure",
                original_error=e
            )
            # The 'return audio_data' line was removed as it's unreachable and incorrect for an async generator.
    
    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=TTSException)
    async def synthesize(self, request: TTSRequest) -> bytes:
        """
        Sintetiza texto usando parámetros del request.
        
        Translates Azure SDK exceptions into domain TTSException.
        """
        try:
            # Ensure synthesizer exists
            if not self._synthesizer:
                self._synthesizer = self.azure_provider.create_synthesizer(
                    voice_name=request.voice_id,
                    audio_mode=self.audio_mode
                )
            
            # Build SSML
            ssml = self._build_ssml(request)
            
            # Synthesize using existing Azure provider method
            audio_data = await self.azure_provider.synthesize_ssml(
                self._synthesizer,
                ssml
            )
            
            if not audio_data:
                raise TTSException(
                    f"Azure synthesis returned no data for voice {request.voice_id}",
                    retryable=True,
                    provider="azure"
                )
            
            return audio_data
        
        # HEXAGONAL: Translate infrastructure exceptions to domain exceptions
        except speechsdk.CancellationReason as e:
            if "authentication" in str(e).lower():
                raise TTSException(
                    "Azure TTS authentication failed",
                    retryable=False,
                    provider="azure",
                    original_error=e
                ) from e
            elif "timeout" in str(e).lower():
                raise TTSException(
                    "Azure TTS timeout",
                    retryable=True,
                    provider="azure",
                    original_error=e
                ) from e
            else:
                raise TTSException(
                    f"Azure TTS canceled: {e}",
                    retryable=False,
                    provider="azure",
                    original_error=e
                ) from e
        
        except TTSException:
            # Re-raise domain exceptions
            raise
        
        except Exception as e:
            logger.error(f"Unexpected TTS error: {e}")
            raise TTSException(
                f"Unexpected synthesis error: {str(e)}",
                retryable=False,
                provider="azure",
                original_error=e
            ) from e
    
    async def synthesize_ssml(self, ssml: str) -> bytes:
        """
        Sintetiza directamente desde SSML.
        
        Translates Azure SDK exceptions into domain TTSException.
        """
        try:
            if not self._synthesizer:
                # Create with default voice if not initialized
                self._synthesizer = self.azure_provider.create_synthesizer(
                    voice_name="es-MX-DaliaNeural",
                    audio_mode=self.audio_mode
                )
            
            audio_data = await self.azure_provider.synthesize_ssml(
                self._synthesizer,
                ssml
            )
            
            if not audio_data:
                raise TTSException(
                    "Azure SSML synthesis returned no data",
                    retryable=True,
                    provider="azure"
                )
            
            return audio_data
        
        # HEXAGONAL: Translate Azure exceptions
        except speechsdk.CancellationReason as e:
            raise TTSException(
                f"Azure SSML synthesis canceled: {e}",
                retryable=False,
                provider="azure",
                original_error=e
            ) from e
        
        except TTSException:
            raise
        
        except Exception as e:
            logger.error(f"Unexpected SSML synthesis error: {e}")
            raise TTSException(
                f"Unexpected error: {str(e)}",
                retryable=False,
                provider="azure",
                original_error=e
            ) from e
    
    def get_available_voices(self, language: Optional[str] = None) -> list[VoiceMetadata]:
        """Obtiene voces de Azure provider y las convierte a VoiceMetadata."""
        voices_raw = self.azure_provider.get_available_voices()
        
        voices = []
        for v in voices_raw:
            # Filter by language if specified
            if language and v.get("locale") != language:
                continue
            
            voices.append(VoiceMetadata(
                id=v["id"],
                name=v["name"],
                gender=v["gender"],
                locale=v["locale"]
            ))
        
        return voices
    
    def get_voice_styles(self, voice_id: str) -> list[str]:
        """Obtiene estilos para una voz específica."""
        styles_dict = self.azure_provider.get_voice_styles()
        return styles_dict.get(voice_id, ["default"])
    
    async def close(self):
        """Limpia recursos de Azure provider."""
        await self.azure_provider.close()
    
    def _build_ssml(self, request: TTSRequest) -> str:
        """Construye SSML desde TTSRequest."""
        style_tag = ""
        if request.style and request.style.lower() != "default":
            style_tag = f'<mstts:express-as style="{request.style}">'
            style_close = '</mstts:express-as>'
        else:
            style_close = ""
        
        # Prosody adjustments
        rate = f"{request.speed}"
        pitch = f"{request.pitch:+.0f}Hz" if request.pitch != 0 else "0Hz"
        volume = f"{request.volume}"
        
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
               xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{request.language}">
            <voice name="{request.voice_id}">
                {style_tag}
                <prosody rate="{rate}" pitch="{pitch}" volume="{volume}">
                    {request.text}
                </prosody>
                {style_close}
            </voice>
        </speak>
        """
        
        return ssml
