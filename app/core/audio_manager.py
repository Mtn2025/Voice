"""
Audio streaming management for VoiceOrchestrator.
Handles TTS queue, background audio, and continuous 20ms streaming.
"""
import asyncio
import base64
import json
import logging


class AudioStreamManager:
    """
    Manages audio streaming (TTS queue + background audio).
    Produces continuous 20ms audio stream to keep telephony line alive.
    Optimized in B9 to reduce CPU usage during silence.
    """

    def __init__(self, websocket, client_type: str = "twilio"):
        """
        Initialize audio stream manager.

        Args:
            websocket: WebSocket connection
            client_type: "twilio", "telnyx", or "browser"
        """
        self.websocket = websocket
        self.client_type = client_type
        self.audio_queue = asyncio.Queue()
        self.background_chunks = []
        self.background_position = 0
        self.stream_active = True

        # Audio chunk size (20ms @ 8kHz mono = 160 bytes)
        self.chunk_size = 160

        # Optimization B9: Pre-calculate silence payload
        # This prevents repeated base64 encoding and JSON serialization 50 times/sec
        self.silence_chunk = b'\x00' * self.chunk_size
        
        # Pre-encode Base64 for silence
        silence_b64 = base64.b64encode(self.silence_chunk).decode('utf-8')
        
        # Pre-build payloads
        self.silence_payload_twilio = json.dumps({
            "event": "media",
            "streamSid": "stream",
            "media": {
                "payload": silence_b64
            }
        })
        self.silence_payload_telnyx = silence_b64 # Telnyx just wants the string

    async def send_audio_chunked(self, audio_data: bytes):
        """
        Queue audio chunks for streaming.
        Breaks down large TTS buffers into 20ms chunks.

        Args:
            audio_data: PCM audio bytes to queue
        """
        # Break into 20ms chunks (160 bytes for telephony)
        for i in range(0, len(audio_data), self.chunk_size):
            chunk = audio_data[i:i + self.chunk_size]

            # Pad if last chunk is short
            if len(chunk) < self.chunk_size:
                chunk = chunk + b'\x00' * (self.chunk_size - len(chunk))

            await self.audio_queue.put(chunk)

    def set_background_audio(self, audio_data: bytes):
        """
        Set background audio (e.g., office ambiance).
        Pre-chunks data to avoid slicing overhead in the hot loop.

        Args:
            audio_data: PCM audio bytes for background loop
        """
        self.background_chunks = []
        self.background_position = 0

        if not audio_data:
            return

        # Pre-slice into 160 byte chunks
        for i in range(0, len(audio_data), self.chunk_size):
            chunk = audio_data[i:i + self.chunk_size]
            if len(chunk) < self.chunk_size:
                chunk = chunk + b'\x00' * (self.chunk_size - len(chunk))
            self.background_chunks.append(chunk)

    async def get_next_chunk(self) -> bytes:
        """
        Get next audio chunk (TTS queue or background).

        Returns:
            160 bytes of PCM audio (20ms @ 8kHz)
        """
        try:
            # Try to get from TTS queue (non-blocking)
            chunk = self.audio_queue.get_nowait()
            return chunk
        except asyncio.QueueEmpty:
            # Fall back to background audio or silence
            if self.background_chunks:
                chunk = self.background_chunks[self.background_position]
                self.background_position = (self.background_position + 1) % len(self.background_chunks)
                return chunk
            
            # Return pre-calculated silence object (identity check possible)
            return self.silence_chunk

    async def stream_loop(self):
        """
        Continuous 20ms audio streaming loop.
        Runs as background task during call.
        """
        logging.info("🎵 Audio stream loop started (Optimized)")

        while self.stream_active:
            # Get next chunk (TTS or background or silence)
            chunk = await self.get_next_chunk()

            try:
                # OPTIMIZATION: Check identity for pre-calculated silence
                if chunk is self.silence_chunk:
                    if self.client_type == "twilio":
                        await self.websocket.send_text(self.silence_payload_twilio)
                    elif self.client_type == "telnyx":
                        await self.websocket.send_text(self.silence_payload_telnyx)
                    elif self.client_type == "browser":
                        await self.websocket.send_bytes(chunk)
                else:
                    # Dynamic content (TTS or Background)
                    if self.client_type == "twilio":
                        # Legacy Twilio Media Stream format
                        payload = {
                            "event": "media",
                            "streamSid": "stream",
                            "media": {
                                "payload": base64.b64encode(chunk).decode('utf-8')
                            }
                        }
                        await self.websocket.send_json(payload)

                    elif self.client_type == "telnyx":
                        # Telnyx format (base64 direct)
                        await self.websocket.send_text(base64.b64encode(chunk).decode('utf-8'))

                    elif self.client_type == "browser":
                        # Browser format (binary)
                        await self.websocket.send_bytes(chunk)

            except Exception as e:
                logging.error(f"❌ Error sending audio: {e}")
                break

            # 20ms delay (50 chunks/second)
            await asyncio.sleep(0.02)

        logging.info("🎵 Audio stream loop stopped")

    def stop(self):
        """Stop the audio stream loop."""
        self.stream_active = False

    async def clear_queue(self):
        """Clear all queued audio chunks."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
