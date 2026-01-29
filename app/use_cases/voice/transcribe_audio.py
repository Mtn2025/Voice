"""Use Case: Transcribe audio to text."""
import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)


class TranscribeAudioUseCase:
    """
    Transcribes audio bytes to text.
    
    Simplified use case that wraps STT provider for testability.
    Since STT is already well-abstracted via recognizer pattern,
    this use case is primarily for consistency and future enhancements.
    
    Responsibilities:
    - Accept audio bytes
    - Call STT provider
    - Return transcribed text
    - Handle empty/invalid audio
    
    Dependencies:
    - STT Provider (AzureProvider with recognizer)
    
    Example:
        >>> from app.core.di_container import get_stt_provider
        >>> provider = get_stt_provider()
        >>> use_case = TranscribeAudioUseCase(provider, config)
        >>> text = await use_case.execute(audio_bytes)
    """
    
    def __init__(self, stt_provider, config):
        """
        Initialize use case with STT provider.
        
        Args:
            stt_provider: Provider with create_recognizer() method
            config: Agent configuration
        """
        self.stt = stt_provider
        self.config = config
        self.recognizer = None
    
    async def initialize(self):
        """
        Initialize STT recognizer.
        
        Should be called once before first use.
        """
        if not self.recognizer:
            try:
                # Create recognizer via provider
                self.recognizer = await self.stt.create_recognizer(
                    sample_rate=getattr(self.config, 'sample_rate', 8000),
                    channels=getattr(self.config, 'channels', 1)
                )
                logger.info("✅ [TranscribeAudio UseCase] Recognizer initialized")
            except Exception as e:
                logger.error(f"❌ [TranscribeAudio UseCase] Failed to initialize recognizer: {e}")
                raise
    
    async def execute(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_data: Raw audio bytes
        
        Returns:
            str: Transcribed text, or None if recognition failed
        
        Example:
            >>> text = await use_case.execute(audio_bytes)
            >>> if text:
            ...     print(f"Recognized: {text}")
        """
        if not audio_data:
            logger.warning("⚠️ [TranscribeAudio UseCase] Empty audio data")
            return None
        
        # Ensure recognizer is initialized
        if not self.recognizer:
            await self.initialize()
        
        logger.debug(f"🎤 [TranscribeAudio UseCase] Transcribing {len(audio_data)} bytes")
        
        try:
            # For streaming STT, we push audio to recognizer
            # This is a simplified version - actual implementation
            # would use the recognizer's streaming API
            
            # Note: The actual transcription happens via the recognizer's
            # event-driven API in the STTProcessor. This use case is more
            # for future enhancements or batch transcription.
            
            # For now, this is a placeholder that delegates to the recognizer
            # In practice, STTProcessor handles streaming recognition
            
            logger.info("ℹ️ [TranscribeAudio UseCase] Streaming STT via recognizer (event-driven)")
            
            # This would be implemented if we need synchronous transcription
            # For now, return None to indicate async/event-driven processing
            return None
            
        except Exception as e:
            logger.error(f"❌ [TranscribeAudio UseCase] Transcription error: {e}")
            return None
    
    async def execute_batch(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio file (batch mode).
        
        Useful for offline transcription or file-based processing.
        
        Args:
            audio_file_path: Path to audio file
        
        Returns:
            str: Transcribed text
        
        Example:
            >>> text = await use_case.execute_batch("/path/to/audio.wav")
        """
        logger.info(f"📄 [TranscribeAudio UseCase] Batch transcription: {audio_file_path}")
        
        try:
            # Read audio file
            import soundfile as sf
            audio_data, sample_rate = sf.read(audio_file_path, dtype='int16')
            
            logger.debug(f"📊 [TranscribeAudio UseCase] Audio file loaded: {len(audio_data)} samples @ {sample_rate}Hz")
            
            # Convert to bytes
            audio_bytes = audio_data.tobytes()
            
            # Use provider's batch transcription if available
            if hasattr(self.stt, 'transcribe_file'):
                result = await self.stt.transcribe_file(audio_file_path)
                logger.info(f"✅ [TranscribeAudio UseCase] Batch transcription complete: {len(result)} chars")
                return result
            else:
                logger.warning("⚠️ [TranscribeAudio UseCase] Batch transcription not supported by provider")
                return None
                
        except Exception as e:
            logger.error(f"❌ [TranscribeAudio UseCase] Batch transcription error: {e}")
            return None
