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

logger = logging.getLogger(__name__)


# --- Static Data (Moved from Legacy Provider) ---
AZURE_VOICES_DATA = [
    # --- Spanish (Mexico) ---
    {"id": "es-MX-DaliaNeural", "name": "Dalia", "gender": "Female", "locale": "es-MX"},
    {"id": "es-MX-JorgeNeural", "name": "Jorge", "gender": "Male", "locale": "es-MX"},
    {"id": "es-MX-BeatrizNeural", "name": "Beatriz", "gender": "Female", "locale": "es-MX"},
    {"id": "es-MX-CandelaNeural", "name": "Candela", "gender": "Female", "locale": "es-MX"},
    {"id": "es-MX-CarlotaNeural", "name": "Carlota", "gender": "Female", "locale": "es-MX"},
    {"id": "es-MX-CecilioNeural", "name": "Cecilio", "gender": "Male", "locale": "es-MX"},
    {"id": "es-MX-GerardoNeural", "name": "Gerardo", "gender": "Male", "locale": "es-MX"},
    {"id": "es-MX-LarissaNeural", "name": "Larissa", "gender": "Female", "locale": "es-MX"},
    {"id": "es-MX-LibertoNeural", "name": "Liberto", "gender": "Male", "locale": "es-MX"},
    {"id": "es-MX-LucianoNeural", "name": "Luciano", "gender": "Male", "locale": "es-MX"},
    {"id": "es-MX-MarinaNeural", "name": "Marina", "gender": "Female", "locale": "es-MX"},
    {"id": "es-MX-NurielNeural", "name": "Nuriel", "gender": "Male", "locale": "es-MX"},
    {"id": "es-MX-PelayoNeural", "name": "Pelayo", "gender": "Male", "locale": "es-MX"},
    {"id": "es-MX-RenataNeural", "name": "Renata", "gender": "Female", "locale": "es-MX"},
    {"id": "es-MX-YagoNeural", "name": "Yago", "gender": "Male", "locale": "es-MX"},

    # --- Spanish (Spain) ---
    {"id": "es-ES-ElviraNeural", "name": "Elvira", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-AlvaroNeural", "name": "Alvaro", "gender": "Male", "locale": "es-ES"},
    {"id": "es-ES-AbrilNeural", "name": "Abril", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-ArnauNeural", "name": "Arnau", "gender": "Male", "locale": "es-ES"},
    {"id": "es-ES-DarioNeural", "name": "Dario", "gender": "Male", "locale": "es-ES"},
    {"id": "es-ES-EliasNeural", "name": "Elias", "gender": "Male", "locale": "es-ES"},
    {"id": "es-ES-EstrellaNeural", "name": "Estrella", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-IreneNeural", "name": "Irene", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-LaiaNeural", "name": "Laia", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-LiaNeural", "name": "Lia", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-NilNeural", "name": "Nil", "gender": "Male", "locale": "es-ES"},
    {"id": "es-ES-SaulNeural", "name": "Saul", "gender": "Male", "locale": "es-ES"},
    {"id": "es-ES-TeoNeural", "name": "Teo", "gender": "Male", "locale": "es-ES"},
    {"id": "es-ES-TrianaNeural", "name": "Triana", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-VeraNeural", "name": "Vera", "gender": "Female", "locale": "es-ES"},
    {"id": "es-ES-XimenaNeural", "name": "Ximena", "gender": "Female", "locale": "es-ES"},

    # --- Spanish (US) ---
    {"id": "es-US-PalomaNeural", "name": "Paloma", "gender": "Female", "locale": "es-US"},
    {"id": "es-US-AlonsoNeural", "name": "Alonso", "gender": "Male", "locale": "es-US"},
    {"id": "es-US-MiguelNeural", "name": "Miguel", "gender": "Male", "locale": "es-US"},

    # --- English (US) ---
    {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-GuyNeural", "name": "Guy", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-AriaNeural", "name": "Aria", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-DavisNeural", "name": "Davis", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-AmberNeural", "name": "Amber", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-AndrewNeural", "name": "Andrew", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-AshleyNeural", "name": "Ashley", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-BrandonNeural", "name": "Brandon", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-BrianNeural", "name": "Brian", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-CoraNeural", "name": "Cora", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-ElizabethNeural", "name": "Elizabeth", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-EricNeural", "name": "Eric", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-JacobNeural", "name": "Jacob", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-JaneNeural", "name": "Jane", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-JasonNeural", "name": "Jason", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-MichelleNeural", "name": "Michelle", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-MonicaNeural", "name": "Monica", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-NancyNeural", "name": "Nancy", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-RogerNeural", "name": "Roger", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-SaraNeural", "name": "Sara", "gender": "Female", "locale": "en-US"},
    {"id": "en-US-SteffanNeural", "name": "Steffan", "gender": "Male", "locale": "en-US"},
    {"id": "en-US-TonyNeural", "name": "Tony", "gender": "Male", "locale": "en-US"}
]

AZURE_VOICE_STYLES = {
    # Mexico
    "es-MX-DaliaNeural": ["customerservice", "chat", "cheerful", "calm", "sad", "angry", "fearful", "disgruntled", "serious", "affectionate", "gentle"],
    "es-MX-JorgeNeural": ["chat", "conversational", "customerservice", "cheerful", "empathetic", "serious"],

    # Spain
    "es-ES-ElviraNeural": ["customerservice", "empathetic", "cheerful", "calm", "chat"],

    # English US
    "en-US-JennyNeural": ["assistant", "chat", "customerservice", "newscast", "angry", "cheerful", "sad", "excited", "friendly", "terrified", "shouting", "unfriendly", "whispering", "hopeful"],
    "en-US-GuyNeural": ["newscast", "angry", "cheerful", "sad", "excited", "friendly", "terrified", "shouting", "unfriendly", "whispering", "hopeful"],
    "en-US-AriaNeural": ["chat", "customerservice", "narration-professional", "newscast-casual", "newscast-formal", "cheerful", "empathetic", "angry", "sad", "excited", "friendly", "terrified", "shouting", "unfriendly", "whispering", "hopeful"],
    "en-US-DavisNeural": ["chat", "angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
    "en-US-JaneNeural": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
    "en-US-JasonNeural": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
    "en-US-NancyNeural": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
    "en-US-SaraNeural": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
    "en-US-TonyNeural": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"]
}


class AzureTTSAdapter(TTSPort):
    """
    Adaptador para Azure TTS que implementa TTSPort.
    """

    def __init__(self, config: Any | None = None, audio_mode: str = "twilio"):
        """
        Args:
            config: Clean config object or None.
            audio_mode: "browser", "twilio", or "telnyx".
        """
        self.api_key = config.api_key if config else settings.AZURE_SPEECH_KEY
        self.region = config.region if config else settings.AZURE_SPEECH_REGION
        self.audio_mode = config.audio_mode if config else audio_mode

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.api_key,
            region=self.region
        )
        self._synthesizer: speechsdk.SpeechSynthesizer | None = None

        # Executor for blocking SDK calls moved to run_in_executor in core
        # We rely on asyncio.to_thread / run_in_executor

    def _create_synthesizer(self, voice_name: str):
        """Creates standard SpeechSynthesizer."""
        self.speech_config.speech_synthesis_voice_name = voice_name

        if self.audio_mode == "browser":
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm)
        elif self.audio_mode == "telnyx":
            # Telnyx (Mexico/Global) -> A-Law 8kHz
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoALaw)
        else:
            # Twilio Default -> Mu-Law 8kHz
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw)

        # Redirect internal output to /dev/null to prevent hardware usage
        audio_config = speechsdk.audio.AudioConfig(filename="/dev/null")

        return speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=TTSException)
    @track_streaming_latency("azure_tts")
    async def synthesize_stream(self, request: TTSRequest) -> AsyncIterator[bytes]:
        """
        Genera audio desde texto en streaming.

        For Azure, we simulate streaming by invoking the full synthesis and yielding chunks,
        or we could use PullAudioOutputStream if we wanted true streaming.
        Due to previous implementation, we wrap the `synthesize` result or use a stream.
        """
        trace_id = request.metadata.get('trace_id', 'unknown')
        start_time = time.time()
        first_byte_time = None
        metrics_collector = get_metrics_collector()

        try:
             # Ensure synthesizer exists
            if not self._synthesizer:
                 self._synthesizer = self._create_synthesizer(request.voice_id)

            # Using PullAudioOutputStream logic or standard async synthesis
            # For simplicity matching previous provider logic which allowed iterating
            # We'll stick to a simpler async call for now to respect the contract

            # NOTE: Azure SDK for Python `start_speaking_ssml_async` returns a PullAudioOutputStream
            # we can read from.

            ssml = self._build_ssml(request)

            # Execute standard synthesis (non-streaming for now, chunked return)
            # True streaming with Azure Python SDK is complex (callbacks/Push/Pull).
            # The previous provider was using speak_text_async and blocking .get().

            # Let's perform the synthesis
            audio_data = await self.synthesize_ssml(ssml)

            # Yield as chunks
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

        # Ensure synthesizer configured (default voice if not set)
        if not self._synthesizer:
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

    def get_available_voices(self, language: str | None = None) -> list[VoiceMetadata]:
        voices = []
        for v in AZURE_VOICES_DATA:
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
        return AZURE_VOICE_STYLES.get(voice_id, ["default"])

    async def close(self):
        """Limpia."""
        pass

    def get_available_languages(self) -> list[str]:
        """Deriva idiomas disponibles de la lista de voces."""
        locales = set()
        for v in AZURE_VOICES_DATA:
            if "locale" in v:
                locales.add(v["locale"])
        return sorted(locales)

    def get_all_voice_styles(self) -> dict[str, list[str]]:
        """Devuelve el mapa completo de estilos (para el Dashboard)."""
        return AZURE_VOICE_STYLES


    def _build_ssml(self, request: TTSRequest) -> str:
        """Construye SSML."""
        style_tag = ""
        if request.style and request.style.lower() != "default":
            style_tag = f'<mstts:express-as style="{request.style}">'
            style_close = '</mstts:express-as>'
        else:
            style_close = ""

        # Determine Rate/Vol/Pitch format
        rate = f"{request.speed}"
        pitch_val = request.provider_options.get('pitch_hz', request.pitch)
        pitch = f"{pitch_val:+.0f}Hz" if pitch_val != 0 else "0Hz"
        volume = f"{request.volume}"

        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{request.language}"><voice name="{request.voice_id}">{style_tag}<prosody rate="{rate}" pitch="{pitch}" volume="{volume}">{request.text}</prosody>{style_close}</voice></speak>"""
        return ssml
