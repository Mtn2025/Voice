
import asyncio
import base64
import contextlib
import json
import logging
import pathlib
from fastapi import WebSocket

from app.core.audio_processor import AudioProcessor

class AudioStreamer:
    """
    Handles the continuous audio stream functionality:
    - Maintaining the 20ms output loop
    - Mixing TTS audio with Background audio
    - Managing the audio queue
    - Sending frames to the WebSocket
    """
    def __init__(self, websocket: WebSocket, client_type: str, stream_id: str | None = None):
        self.websocket = websocket
        self.client_type = client_type
        self.stream_id = stream_id
        
        # Audio State
        self.audio_queue = asyncio.Queue()
        self.bg_loop_buffer: bytes | None = None
        self.bg_loop_index = 0
        self.stream_task: asyncio.Task | None = None

    async def start(self):
        """Starts the continuous audio stream loop (mainly for telephony scenarios)."""
        if self.client_type != "browser":
             logging.info("🌊 [STREAM] Launching Audio Stream Loop...")
             self.stream_task = asyncio.create_task(self._audio_stream_loop())

    async def stop(self):
        """Stops the audio stream loop."""
        if self.stream_task:
            logging.info("🌊 [STREAM] Stopping Audio Stream Loop...")
            self.stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.stream_task
            self.stream_task = None

    def load_background_audio(self, bg_sound_name: str | None) -> None:
        """Loads background audio (WAV/Raw) if configured."""
        if not bg_sound_name or bg_sound_name.lower() == 'none' or self.client_type == 'browser':
             return

        try:
             # Basic security check to prevent directory traversal
             safe_name = bg_sound_name.replace("..", "").replace("/", "") 
             sound_path = pathlib.Path(f"app/static/sounds/{safe_name}.wav")

             if sound_path.exists():
                 logging.info(f"🎵 [BG-SOUND] Loading background audio: {sound_path}")
                 with open(sound_path, "rb") as f:
                     raw_bytes = f.read()

                 # WAV Header Parsing (Find 'data' chunk) to skip header noise
                 data_index = raw_bytes.find(b'data')

                 if data_index != -1:
                     # 'data' (4) + Size (4) = 8 bytes offset
                     start_offset = data_index + 8
                     self.bg_loop_buffer = raw_bytes[start_offset:]
                     logging.info(f"🎵 [BG-SOUND] WAV Header found (Offset {start_offset}). Loaded payload.")
                 else:
                     # Fallback: Assume RAW or headerless
                     self.bg_loop_buffer = raw_bytes
                     logging.warning("⚠️ [BG-SOUND] No 'data' chunk found in WAV. Assuming RAW Mono.")

                 logging.info(f"🎵 [BG-SOUND] Buffer Ready. Size: {len(self.bg_loop_buffer)}")
             else:
                 logging.warning(f"⚠️ [BG-SOUND] File not found: {sound_path}. Mixing disabled.")
        except Exception as e_bg:
             logging.error(f"❌ [BG-SOUND] Failed to load: {e_bg}")

    async def send_audio_chunked(self, audio_data: bytes) -> None:
        """
        PRODUCER: Queues audio chunks for the continuous stream loop.
        Breaks down large TTS buffers into 20ms chunks (160 bytes for telephony).
        """
        if self.client_type == "browser":
             # Browser still uses direct send
             b64 = base64.b64encode(audio_data).decode("utf-8")
             logging.debug(f"📤 [BROWSER] Sending audio chunk: {len(audio_data)} bytes")
             try:
                 await self.websocket.send_text(json.dumps({"type": "audio", "data": b64}))
             except Exception:
                 pass
             return

        # For Telephony: Queue slices
        chunk_size = 160
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i : i + chunk_size]
            self.audio_queue.put_nowait(chunk)

    async def _audio_stream_loop(self) -> None:
        """
        CONSUMER: Continuous 20ms Loop.
        Mixes Background Audio + TTS Queue -> Socket.
        Ensures constant stream (Carrier) to keep line alive and ambiance smooth.
        """
        logging.info("🌊 [STREAM] Starting Continuous Audio Stream Loop")
        try:
            loop = asyncio.get_running_loop()
            while True:
                if self.websocket.client_state == 3: # PREVENT CRASH ON CLOSED SOCKET
                    break

                # 1. TIMING: Target 20ms (0.02s)
                loop_start = loop.time()

                # 2. FETCH TTS (Non-blocking)
                tts_chunk = None
                with contextlib.suppress(asyncio.QueueEmpty):
                    tts_chunk = self.audio_queue.get_nowait()

                # 3. FETCH BACKGROUND (If connected)
                bg_chunk = self._get_next_background_chunk(len(tts_chunk) if tts_chunk else 160)

                # 4. MIXING LOGIC
                final_chunk = self._mix_audio(tts_chunk, bg_chunk)

                # 5. SEND (If we have something to send)
                if final_chunk:
                    await self._send_audio_chunk(final_chunk)

                # 6. SLEEP (Keep sync)
                elapsed = loop.time() - loop_start
                if elapsed < 0.02:
                    await asyncio.sleep(0.02 - elapsed)

        except asyncio.CancelledError:
             logging.info("🌊 [STREAM] Loop Cancelled")
        except Exception as e_loop:
             logging.error(f"🌊 [STREAM] Loop Crash: {e_loop}")

    def _get_next_background_chunk(self, req_len: int) -> bytes | None:
        """Retrieves the next chunk of background audio from the buffer."""
        if not self.bg_loop_buffer or len(self.bg_loop_buffer) == 0:
            return None

        bg_chunk = None
        if self.bg_loop_index + req_len > len(self.bg_loop_buffer):
            part1 = self.bg_loop_buffer[self.bg_loop_index:]
            remaining = req_len - len(part1)
            part2 = self.bg_loop_buffer[:remaining]
            bg_chunk = part1 + part2
            self.bg_loop_index = remaining
        else:
            bg_chunk = self.bg_loop_buffer[self.bg_loop_index : self.bg_loop_index + req_len]
            self.bg_loop_index += req_len
        return bg_chunk

    def _mix_audio(self, tts_chunk: bytes | None, bg_chunk: bytes | None) -> bytes | None:
        """Mixes TTS and Background audio chunks using AudioProcessor (NumPy)."""
        if tts_chunk and bg_chunk:
            # MIX
            try:
                # Optimized mixing: Assume uLaw/aLaw based on client type
                # Note: This logic assumes 8kHz for telephony
                is_alaw = (self.client_type == 'telnyx')
                
                if is_alaw:
                     bg_lin = AudioProcessor.alaw2lin(bg_chunk, 2)
                     tts_lin = AudioProcessor.alaw2lin(tts_chunk, 2)
                else:
                     bg_lin = AudioProcessor.alaw2lin(bg_chunk, 2) # Often BG files are same format, but check?
                     # Wait, original code used alaw2lin for BG always?
                     # Re-checking original code: "bg_lin = AudioProcessor.alaw2lin(bg_chunk, 2)" always.
                     # This implies the BG files are expected to be G.711 A-law encoded or just treated as such.
                     # Let's keep original logic.
                     tts_lin = AudioProcessor.ulaw2lin(tts_chunk, 2)

                bg_lin_quiet = AudioProcessor.mul(bg_lin, 2, 0.15)
                mixed_lin = AudioProcessor.add(tts_lin, bg_lin_quiet, 2)

                if is_alaw:
                    final_chunk = AudioProcessor.lin2alaw(mixed_lin, 2)
                else:
                    final_chunk = AudioProcessor.lin2ulaw(mixed_lin, 2)
                return final_chunk
            except Exception as e_mix:
                logging.error(f"Mixing error: {e_mix}")
                return tts_chunk # Fallback

        elif tts_chunk:
            return tts_chunk

        elif bg_chunk:
            # JUST BACKGROUND
            try:
                bg_lin = AudioProcessor.alaw2lin(bg_chunk, 2)
                bg_lin_quiet = AudioProcessor.mul(bg_lin, 2, 0.15) # Quiet BG

                if self.client_type == 'telnyx':
                    final_chunk = AudioProcessor.lin2alaw(bg_lin_quiet, 2)
                else:
                    final_chunk = AudioProcessor.lin2ulaw(bg_lin_quiet, 2)
                return final_chunk
            except Exception:
                return None
        return None

    async def _send_audio_chunk(self, final_chunk: bytes) -> None:
        """Encodes and sends audio chunk via WebSocket."""
        try:
            b64_audio = base64.b64encode(final_chunk).decode("utf-8")
            msg = {
                "event": "media",
                "media": {"payload": b64_audio}
            }
            if self.client_type == "twilio":
                msg["streamSid"] = self.stream_id
            elif self.client_type == "telnyx":
                msg["stream_id"] = self.stream_id

            await self.websocket.send_text(json.dumps(msg))
        except Exception:
            # Socket likely closed or error, suppress to avoid loop crash
            pass
