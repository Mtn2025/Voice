"""Use Case: Synthesize text to speech."""
import logging
from typing import Optional
from app.domain.value_objects.voice_config import VoiceConfig
from app.utils.ssml_builder import build_azure_ssml

logger = logging.getLogger(__name__)


class SynthesizeTextUseCase:
    """
    Synthesizes text to audio bytes.
    
    This use case encapsulates the business logic for text-to-speech synthesis,
    making it testable without Pipeline or WebSocket dependencies.
    
    Responsibilities:
    - Build SSML from text + voice config
    - Call TTS provider (via interface)
    - Return audio bytes
    - Handle empty text gracefully
    
    Dependencies:
    - TTS Provider (any object with synthesize_ssml() or synthesize() method)
    
    Example:
        >>> provider = get_tts_provider()
        >>> use_case = SynthesizeTextUseCase(provider)
        >>> voice_config = VoiceConfig(name="es-MX-DaliaNeural", speed=1.2)
        >>> audio = await use_case.execute("Hola mundo", voice_config)
    """
    
    def __init__(self, tts_provider):
        """
        Initialize use case with TTS provider.
        
        Args:
            tts_provider: Provider implementing synthesize_ssml() method
                         (legacy interface) or synthesize() (hexagonal port)
        """
        self.tts = tts_provider
    
    async def execute(self, text: str, voice_config: VoiceConfig) -> bytes:
        """
        Synthesize text to audio bytes.
        
        Args:
            text: Text to synthesize
            voice_config: Voice configuration (immutable value object)
        
        Returns:
            bytes: Audio data in configured format
            
        Raises:
            Exception: If synthesis fails (propagated from provider)
        
        Example:
            >>> audio = await use_case.execute("Hola", voice_config)
            >>> len(audio)  # e.g., 16000 bytes
        """
        # Handle empty text
        if not text or not text.strip():
            logger.warning("⚠️ [SynthesizeText UseCase] Empty text provided")
            return b""
        
        logger.info(f"🗣️ [SynthesizeText UseCase] Synthesizing {len(text)} chars with voice {voice_config.name}")
        
        # Build SSML using value object
        ssml_params = voice_config.to_ssml_params()
        ssml = build_azure_ssml(text=text, **ssml_params)
        
        logger.debug(f"📄 [SynthesizeText UseCase] SSML generated: {len(ssml)} chars")
        
        # Synthesize using provider
        # Support both legacy interface (synthesize_ssml) and hexagonal port (synthesize)
        try:
            if hasattr(self.tts, 'synthesize_ssml'):
                # Legacy provider interface
                audio_data = await self.tts.synthesize_ssml(ssml)
            elif hasattr(self.tts, 'synthesize'):
                # Hexagonal port interface (future)
                from app.domain.ports.tts_port import TTSRequest
                request = TTSRequest(ssml=ssml, voice=voice_config.name)
                audio_data = await self.tts.synthesize(request)
            else:
                raise TypeError(
                    f"TTS provider {type(self.tts).__name__} doesn't support "
                    "synthesize_ssml() or synthesize() methods"
                )
        except Exception as e:
            logger.error(f"❌ [SynthesizeText UseCase] Synthesis failed: {e}")
            raise
        
        logger.info(f"✅ [SynthesizeText UseCase] Generated {len(audio_data)} bytes of audio")
        
        return audio_data
    
    async def execute_with_fallback(
        self, 
        text: str, 
        voice_config: VoiceConfig,
        fallback_text: Optional[str] = None
    ) -> bytes:
        """
        Synthesize with fallback text if primary synthesis fails.
        
        Useful for graceful degradation in production.
        
        Args:
            text: Primary text to synthesize
            voice_config: Voice configuration
            fallback_text: Fallback text if primary fails
        
        Returns:
            bytes: Audio data (from primary or fallback)
        """
        try:
            return await self.execute(text, voice_config)
        except Exception as e:
            if fallback_text:
                logger.warning(
                    f"⚠️ [SynthesizeText UseCase] Primary synthesis failed, using fallback. "
                    f"Error: {e}"
                )
                return await self.execute(fallback_text, voice_config)
            raise
