"""
Mock Telephony Adapter - Simulates WebSocket/Twilio connection.

For local testing without real telephony infrastructure.
"""
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class MockTelephonyAdapter:
    """
    Mock adapter that simulates telephony WebSocket connection.
    
    Simulates:
    - Incoming audio streams
    - Outgoing audio transmission
    - Connection lifecycle (connect, disconnect)
    - Latency simulation
    """
    
    def __init__(self, latency_ms: int = 50):
        """
        Args:
            latency_ms: Simulated network latency in milliseconds
        """
        self.latency_ms = latency_ms
        self.connected = False
        self.audio_callback: Optional[Callable] = None
        self.transmitted_audio = []  # For inspection
        self._connection_time: Optional[datetime] = None
    
    async def connect(self):
        """Simulate connection establishment."""
        await asyncio.sleep(self.latency_ms / 1000)
        self.connected = True
        self._connection_time = datetime.now()
        logger.info(f"📞 [MockTelephony] Connected (simulated latency: {self.latency_ms}ms)")
    
    async def disconnect(self):
        """Simulate disconnection."""
        self.connected = False
        duration = (datetime.now() - self._connection_time).total_seconds() if self._connection_time else 0
        logger.info(f"📞 [MockTelephony] Disconnected (duration: {duration:.2f}s)")
    
    def register_audio_callback(self, callback: Callable):
        """
        Register callback for incoming audio.
        
        Args:
            callback: Async function to call with audio data
        """
        self.audio_callback = callback
        logger.debug("[MockTelephony] Audio callback registered")
    
    async def send_audio(self, audio_data: bytes):
        """
        Simulate sending audio data (TTS output).
        
        Args:
            audio_data: Audio bytes to transmit
        """
        if not self.connected:
            raise RuntimeError("Cannot send audio: Not connected")
        
        # Simulate network latency
        await asyncio.sleep(self.latency_ms / 1000)
        
        self.transmitted_audio.append({
            'timestamp': datetime.now(),
            'size': len(audio_data)
        })
        
        logger.debug(f"🔊 [MockTelephony] Sent {len(audio_data)} bytes audio")
    
    async def inject_incoming_audio(self, audio_data: bytes):
        """
        Inject incoming audio (simulates user speaking).
        
        Args:
            audio_data: Simulated audio from user
        """
        if not self.connected:
            logger.warning("[MockTelephony] Cannot inject audio: Not connected")
            return
        
        if self.audio_callback:
            # Simulate network latency
            await asyncio.sleep(self.latency_ms / 1000)
            await self.audio_callback(audio_data)
        else:
            logger.warning("[MockTelephony] No audio callback registered")
    
    def get_stats(self) -> dict:
        """Get transmission statistics."""
        return {
            'connected': self.connected,
            'latency_ms': self.latency_ms,
            'audio_packets_sent': len(self.transmitted_audio),
            'connection_duration': (datetime.now() - self._connection_time).total_seconds() if self._connection_time else 0
        }
