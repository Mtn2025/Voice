"""
Adaptador Azure TTS - Implementación de TTSPort.

Wrappea la lógica de síntesis de voz de Azure Speech SDK.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import azure.cognitiveservices.speech as speechsdk
from circuitbreaker import circuit

from app.core.config import settings
from app.core.decorators import track_streaming_latency
from app.domain.ports import TTSException, TTSPort, TTSRequest, VoiceMetadata
from app.observability import get_metrics_collector
from app.adapters.outbound.tts.azure_voice_styles import get_voice_styles_spanish

logger = logging.getLogger(__name__)



# --- Cache for Dynamic Data ---
_VOICE_CACHE: list[dict] = []
_STYLE_CACHE: dict[str, list[str]] = {}
_LAST_CACHE_UPDATE: float = 0
CACHE_TTL = 3600  # 1 hour


from app.core.audio_config import AudioConfig

class AzureTTSAdapter(TTSPort):
    """
    Adaptador para Azure TTS que implementa TTSPort.
    """

    def __init__(self, config: Any | None = None, audio_mode: str = "twilio", audio_config: AudioConfig | None = None):
        """
        Args:
            config: Clean config object or None.
            audio_mode: "browser", "twilio", or "telnyx" (Legacy).
            audio_config: Explicit audio configuration.
        """
        self.api_key = config.api_key if config else settings.AZURE_SPEECH_KEY
        self.region = config.region if config else settings.AZURE_SPEECH_REGION

        # Audio Config Logic
        if audio_config:
            self.audio_config = audio_config
        else:
            legacy_mode = config.audio_mode if config else audio_mode
            logger.warning(f"⚠️ [AzureTTS] Using legacy audio_mode: {legacy_mode}")
            self.audio_config = AudioConfig.from_legacy_mode(legacy_mode)

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.api_key,
            region=self.region
        )
        self._synthesizer: speechsdk.SpeechSynthesizer | None = None

    def _create_synthesizer(self, voice_name: str | None = None):
        """Creates standard SpeechSynthesizer."""
        if voice_name:
            self.speech_config.speech_synthesis_voice_name = voice_name

        # Determine Output Format based on AudioConfig
        if self.audio_config.encoding == "pcm":
             # 16kHz PCM (Browser)
             self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm)
        elif self.audio_config.encoding == "alaw":
             self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoALaw)
        else:
             # Default fallback mulaw 8khz
             self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw)

        audio_config = speechsdk.audio.AudioConfig(filename="/dev/null")

        return speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

    async def _ensure_voices_loaded(self):
        """
        Fetches voices from Azure if cache is empty or expired.

        Official Method Verified: `speech_synthesizer.get_voices_async()`
        Source: https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechsynthesizer?view=azure-python#azure-cognitiveservices-speech-speechsynthesizer-get-voices-async
        """
        global _VOICE_CACHE, _STYLE_CACHE, _LAST_CACHE_UPDATE
        
        current_time = time.time()
        if _VOICE_CACHE and (current_time - _LAST_CACHE_UPDATE < CACHE_TTL):
            return

        logger.info("☁️ [Azure TTS] Fetching fresh voice list from Azure API...")
        
        loop = asyncio.get_running_loop()
        
        def _fetch_blocking():
            # Use a temporary synthesizer for fetching voices (no voice_name needed)
            # IMPORTANT: Authentication must be valid here
            synth = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=None)
            result = synth.get_voices_async().get()
            
            if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
                return result.voices
            else:
                logger.error(f"❌ [Azure TTS] Failed to list voices: {result.error_details}")
                return []

        try:
            voices = await loop.run_in_executor(None, _fetch_blocking)
            
            new_voice_cache = []
            new_style_cache = {}

            for v in voices:
                # Extract metadata
                voice_entry = {
                    "id": v.name,              # e.g., "es-MX-DaliaNeural"
                    "name": v.local_name,      # e.g., "Dalia"
                    "gender": v.gender.name,   # e.g., "Female"
                    "locale": v.locale         # e.g., "es-MX"
                }
                new_voice_cache.append(voice_entry)
                
                # Extract styles if available - TRADUCIDOS AL ESPAÑOL
                # Azure usage: v.style_list produces a list of strings (in English)
                # We translate them to Spanish using official mapping
                if v.style_list:
                    # Get Spanish translations for this specific voice
                    spanish_styles = get_voice_styles_spanish(v.name)
                    new_style_cache[v.name] = spanish_styles
                else:
                    new_style_cache[v.name] = []

            # Atomic update
            _VOICE_CACHE = new_voice_cache
            _STYLE_CACHE = new_style_cache
            _LAST_CACHE_UPDATE = current_time
            logger.info(f"✅ [Azure TTS] Cached {len(_VOICE_CACHE)} voices and styles.")

        except Exception as e:
            logger.error(f"❌ [Azure TTS] Error fetching voices: {e}")
            # Fallback not implemented to force real connectivity check as requested by user
            # If API fails, lists will be empty.

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=TTSException)
    @track_streaming_latency("azure_tts")
    async def synthesize_stream(self, request: TTSRequest) -> AsyncIterator[bytes]:
        """Genera audio desde texto en streaming."""
        trace_id = request.metadata.get('trace_id', 'unknown')
        start_time = time.time()
        first_byte_time = None
        metrics_collector = get_metrics_collector()

        try:
            if not self._synthesizer:
                self._synthesizer = self._create_synthesizer(request.voice_id)

            ssml = self._build_ssml(request)
            audio_data = await self.synthesize_ssml(ssml)

            chunk_size = 4096
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                if first_byte_time is None:
                    first_byte_time = time.time()
                    ttfb = (first_byte_time - start_time) * 1000
                    logger.info(f"[TTS Azure] trace={trace_id} TTFB={ttfb:.0f}ms voice={request.voice_id}")
                yield chunk

            total_time = (time.time() - start_time) * 1000
            await metrics_collector.record_latency(trace_id, 'tts', total_time)

        except Exception as e:
            logger.error(f"[TTS Azure] trace={trace_id} ERROR: {e!s}")
            raise TTSException(f"Azure TTS synthesis failed: {e!s}", retryable=True, provider="azure") from e

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=TTSException)
    async def synthesize(self, request: TTSRequest) -> bytes:
        """Sintetiza texto usando parámetros del request."""
        try:
            if not self._synthesizer:
                self._synthesizer = self._create_synthesizer(request.voice_id)
            ssml = self._build_ssml(request)
            return await self.synthesize_ssml(ssml)
        except Exception as e:
             raise TTSException(f"Synthesis failed: {e}", retryable=True, provider="azure") from e

    async def synthesize_ssml(self, ssml: str) -> bytes:
        """Sintetiza directamente desde SSML."""
        if not self._synthesizer:
             # Default fallback if simple synthesize called without context
             self._synthesizer = self._create_synthesizer("es-MX-DaliaNeural")

        loop = asyncio.get_running_loop()

        def _blocking_synthesis():
            result = self._synthesizer.speak_ssml_async(ssml).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                raise Exception(f"Synthesis canceled: {cancellation_details.reason}. Error details: {cancellation_details.error_details}")
            return None

        try:
            audio_data = await loop.run_in_executor(None, _blocking_synthesis)
            if not audio_data:
                raise Exception("No audio data returned")
            return audio_data
        except Exception as e:
             logger.error(f"SSML Synthesis error: {e}")
             raise TTSException(f"Azure SSML Error: {e}", retryable=True, provider="azure") from e

    async def get_available_voices(self, language: str | None = None) -> list[VoiceMetadata]:
        await self._ensure_voices_loaded()
        
        voices = []
        for v in _VOICE_CACHE:
            if language and v.get("locale") != language:
                continue
            voices.append(VoiceMetadata(
                id=v["id"],
                name=v["name"],
                gender=v["gender"],
                locale=v["locale"]
            ))
        return voices

    async def get_voice_styles(self, voice_id: str) -> list[str]:
        await self._ensure_voices_loaded()
        return _STYLE_CACHE.get(voice_id, [])

    async def close(self):
        """Limpia."""
        pass

    async def get_available_languages(self) -> list[str]:
        """Deriva idiomas disponibles de la lista de voces."""
        await self._ensure_voices_loaded()
        
        locales = set()
        for v in _VOICE_CACHE:
            if "locale" in v:
                locales.add(v["locale"])
        return sorted(locales)

    async def get_all_voice_styles(self) -> dict[str, list[str]]:
        """Devuelve el mapa completo de estilos (para el Dashboard)."""
        await self._ensure_voices_loaded()
        return _STYLE_CACHE

    def _build_ssml(self, request: TTSRequest) -> str:
        """Construye SSML."""
        style_tag = ""
        if request.style and request.style.lower() != "default":
            style_tag = f'<mstts:express-as style="{request.style}">'
            style_close = '</mstts:express-as>'
        else:
            style_close = ""

        rate = f"{request.speed}"
        pitch_val = request.provider_options.get('pitch_hz', request.pitch)
        pitch = f"{pitch_val:+.0f}Hz" if pitch_val != 0 else "0Hz"
        volume = f"{request.volume}"

        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{request.language}"><voice name="{request.voice_id}">{style_tag}<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">{request.text}</prosody>{style_close}</voice></speak>"""
        return ssml
