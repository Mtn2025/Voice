import logging
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.domain.ports.tts_port import TTSPort, TTSRequest

logger = logging.getLogger(__name__)

class ElevenLabsAdapter(TTSPort):
    """
    Adapter for ElevenLabs TTS API.
    Supports advanced controls: Stability, Similarity, Style, Speaker Boost.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech"

    async def synthesize(self, request: TTSRequest) -> AsyncGenerator[bytes, None]:
        """
        Synthesizes audio using ElevenLabs API.
        Current status: Placeholder/Skeleton for Phase II.
        """
        voice_id = request.voice_id or "21m00Tcm4TlvDq8ikWAM" # Default: Rachel
        # TODO: Use model_id when implementing:
        # model_id = "eleven_turbo_v2" if request.latency_optimization > 0 else "eleven_multilingual_v2"

        # 1. Map Config to API Params
        # stability = request.stability (0.0 - 1.0)
        # similarity = request.similarity_boost
        # style = request.style_exaggeration
        # boost = request.speaker_boost

        logger.info(f"🧪 [ELEVENLABS] Synthesizing: '{request.text[:30]}...' with Voice: {voice_id}")
        logger.debug(f"   Stability: {getattr(request, 'voice_stability', 'N/A')}")

        # Mock Implementation for now (yielding empty bytes to prevent crash if selected)
        # Real implementation requires aiohttp call to /stream

        if not self.api_key:
             logger.error("❌ [ELEVENLABS] No API Key found.")
             return

        # TODO: Implement real API call
        # async with aiohttp.ClientSession() as session:
        #     payload = { ... }
        #     async with session.post(url, json=payload) as resp:
        #         async for chunk in resp.content.iter_chunked(1024):
        #             yield chunk

        logger.warning("⚠️ [ELEVENLABS] Not fully implemented. Returning silence.")
        yield b'\x00' * 320 # 20ms of silence
