"""Audio Manager - Handles audio streaming, queuing and chunking."""
import asyncio
import logging
from typing import Optional
from app.ports.transport import AudioTransport

logger = logging.getLogger(__name__)


class AudioManager:
    """
    Manages audio output streaming and background audio.
    
    Responsibilities:
    - Audio queue management
    - Chunked audio transmission
    - Background audio looping
    - Stream lifecycle management
    
    Extracted from VoiceOrchestrator to reduce complexity.
    """
    
    def __init__(self, transport: AudioTransport, client_type: str = "twilio"):
        """
        Initialize AudioManager.
        
        Args:
            transport: Audio transport interface (WebSocket wrapper)
            client_type: "browser", "twilio", or "telnyx"
        """
        self.transport = transport
        self.client_type = client_type
        
        # Audio Queue
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        
        # Background Audio State
        self.bg_loop_buffer: Optional[bytes] = None
        self.bg_loop_index: int = 0
        
        # Stream Task
        self.stream_task: Optional[asyncio.Task] = None
        
        # Encoding
        self.audio_encoding = "PCMU"  # Default for telephony
        
        # Bot speaking state
        self.is_bot_speaking = False
    
    async def start(self):
        """Start audio streaming loop."""
        if not self.stream_task:
            self.stream_task = asyncio.create_task(self._audio_stream_loop())
            logger.info("🔊 [AudioManager] Stream loop started")
    
    async def stop(self):
        """Stop audio streaming and cleanup."""
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
            self.stream_task = None
            logger.info("🔇 [AudioManager] Stream loop stopped")
    
    async def send_audio_chunked(self, audio_data: bytes) -> None:
        """
        Queue audio for chunked transmission.
        
        For telephony (Twilio/Telnyx): chunks to 160 bytes (20ms @ 8kHz)
        For browser: sends full blob
        
        Args:
            audio_data: Raw audio bytes to transmit
        """
        if not audio_data:
            logger.warning("⚠️ [AudioManager] Empty audio_data received")
            return
        
        logger.debug(f"📤 [AudioManager] Queuing {len(audio_data)} bytes for transmission")
        
        # Mark bot as speaking
        self.is_bot_speaking = True
        
        await self.audio_queue.put(audio_data)
    
    async def clear_queue(self):
        """Clear all pending audio from queue."""
        count = 0
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.task_done()
                count += 1
            except asyncio.QueueEmpty:
                break
        
        if count > 0:
            logger.info(f"🗑️ [AudioManager] Cleared {count} audio chunks from queue")
    
    async def interrupt_speaking(self):
        """Interrupt current speech and clear queue."""
        logger.info("🛑 [AudioManager] Interrupting speech")
        await self.clear_queue()
        self.is_bot_speaking = False
    
    def set_background_audio(self, audio_buffer: bytes):
        """
        Set background audio loop buffer.
        
        Args:
            audio_buffer: Audio to loop during silence
        """
        self.bg_loop_buffer = audio_buffer
        self.bg_loop_index = 0
        logger.info(f"🎵 [AudioManager] Background audio set ({len(audio_buffer)} bytes)")
    
    async def _audio_stream_loop(self):
        """
        Main audio streaming loop.
        
        Continuously transmits audio chunks from queue or background audio.
        """
        logger.info("🔊 [AudioManager] Audio stream loop started")
        
        while True:
            try:
                # Try to get audio from queue (non-blocking with timeout)
                try:
                    audio_blob = await asyncio.wait_for(
                        self.audio_queue.get(), 
                        timeout=0.1
                    )
                    
                    # Transmit queued audio
                    await self._transmit_audio(audio_blob)
                    self.audio_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No queued audio - send background audio if available
                    if self.bg_loop_buffer and not self.is_bot_speaking:
                        await self._transmit_background_audio()
                    else:
                        # Small sleep to prevent busy loop
                        await asyncio.sleep(0.02)
            
            except asyncio.CancelledError:
                logger.info("🔇 [AudioManager] Stream loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ [AudioManager] Stream loop error: {e}", exc_info=True)
                await asyncio.sleep(0.1)
        
        logger.info("🔇 [AudioManager] Audio stream loop stopped")
    
    async def _transmit_audio(self, audio_blob: bytes):
        """
        Transmit audio blob with chunking based on client type.
        
        Args:
            audio_blob: Audio data to transmit
        """
        if self.client_type == "browser":
            # Browser: send full blob
            await self.transport.send_audio(audio_blob)
            logger.debug(f"📤 [AudioManager] Sent {len(audio_blob)} bytes (browser)")
        else:
            # Telephony: chunk to 160 bytes (20ms @ 8kHz mulaw)
            chunk_size = 160
            for i in range(0, len(audio_blob), chunk_size):
                chunk = audio_blob[i:i + chunk_size]
                await self.transport.send_audio(chunk)
            
            logger.debug(f"📤 [AudioManager] Sent {len(audio_blob)} bytes in {len(audio_blob)//chunk_size} chunks")
        
        # Mark as not speaking once transmission complete
        if self.audio_queue.empty():
            self.is_bot_speaking = False
            logger.debug("✅ [AudioManager] All audio transmitted, bot no longer speaking")
    
    async def _transmit_background_audio(self):
        """Transmit background audio chunk (160 bytes for telephony)."""
        if not self.bg_loop_buffer:
            return
        
        chunk_size = 160
        chunk = self.bg_loop_buffer[
            self.bg_loop_index : self.bg_loop_index + chunk_size
        ]
        
        if len(chunk) < chunk_size:
            # Loop back to start
            self.bg_loop_index = 0
            chunk = self.bg_loop_buffer[0:chunk_size]
        else:
            self.bg_loop_index += chunk_size
        
        await self.transport.send_audio(chunk)
        await asyncio.sleep(0.02)  # 20ms cadence
