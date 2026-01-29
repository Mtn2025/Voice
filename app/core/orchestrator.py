
import asyncio
import base64
import json
import logging
import time
import uuid
import contextlib
from typing import Optional

from fastapi import WebSocket

from app.core.config import settings
from app.core.service_factory import ServiceFactory
from app.services.db_service import db_service
from app.db.database import AsyncSessionLocal
from app.core.audio_processor import AudioProcessor # For mixing/codec if needed in transport
from app.ports.transport import AudioTransport

# Pipeline
from app.core.pipeline import Pipeline
from app.core.frames import AudioFrame, TextFrame, CancelFrame, StartFrame, EndFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
# Processors
from app.processors.logic.stt import STTProcessor
from app.processors.logic.vad import VADProcessor
from app.processors.logic.aggregator import ContextAggregator
from app.processors.logic.llm import LLMProcessor
from app.processors.logic.tts import TTSProcessor
from app.processors.logic.metrics import MetricsProcessor
from app.processors.logic.metrics import MetricsProcessor
from app.processors.output.audio_sink import PipelineOutputSink
from app.processors.logic.reporter import TranscriptReporter  # NEW

logger = logging.getLogger(__name__)

class VoiceOrchestrator:
    """
    Refactored Lightweight Orchestrator (Pipecat-style).
    Role:
    1. Manage WebSocket Connection (Input/Output).
    2. Initialize and Host the Pipeline.
    3. Route Input Audio -> Pipeline.
    4. Provide 'Transport' methods for Sync/Output (send_audio_chunked).
    """
    def __init__(self, transport: AudioTransport, client_type: str = "twilio", initial_context: Optional[str] = None) -> None:
        self.transport = transport
        self.client_type = client_type
        self.initial_context_token = initial_context # Base64 string from Telnyx
        self.initial_context_data = {} # Decoded dict
        self.stream_id: Optional[str] = None
        self.call_db_id: Optional[int] = None
        self.config = None
        self.conversation_history = []
        
        # Initialize Managers (NEW - Clean Architecture)
        from app.core.managers import AudioManager, CRMManager
        
        self.audio_manager = AudioManager(transport, client_type)
        self.crm_manager: Optional[CRMManager] = None  # Initialized after config load
        
        # Pipeline
        self.pipeline: Optional[Pipeline] = None
        
        # Providers (Managed by Processors, but created here via Factory)
        self.stt_provider = None
        self.llm_provider = None
        self.tts_provider = None
        
        # Loop
        self.loop = None
        
        # State
        self.start_time = time.time()
        self.last_interaction_time = time.time()
        self.monitor_task = None

        # Decode Context if present
        if self.initial_context_token:
            try:
                decoded = base64.b64decode(self.initial_context_token).decode("utf-8")
                self.initial_context_data = json.loads(decoded)
                logger.info(f"📋 [CTX] Injected Variables: {self.initial_context_data.keys()}")
            except Exception as e:
                logger.warning(f"Failed to decode context: {e}")

    async def monitor_idle(self) -> None:
        logging.warning("🏁 [MONITOR] Starting monitor_idle loop...")
        while True:
            await asyncio.sleep(1.0)
            try:
                now = time.time()

                # Max Duration Check
                max_dur = getattr(self.config, 'max_duration', 600)
                if now - self.start_time > max_dur:
                     logging.info("🛑 Max duration reached. Ending call.")
                     await self.stop()
                     break

                # Idle Check (Only if not speaking)
                idle_timeout = getattr(self.config, 'idle_timeout', 10.0)
                
                # Update last_interaction if we are speaking
                if self.is_bot_speaking:
                    self.last_interaction_time = now

                if not self.is_bot_speaking and (now - self.last_interaction_time > idle_timeout) and await self._handle_idle_timeout_logic(now):
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                 logging.warning(f"Monitor error: {e}")

    async def _handle_idle_timeout_logic(self, now: float) -> bool:
        if not hasattr(self, 'idle_retries'):
             self.idle_retries = 0

        max_retries = getattr(self.config, 'inactivity_max_retries', 3)
        logging.warning(f"zzz Idle timeout reached. Retry {self.idle_retries + 1}/{max_retries}")

        if self.idle_retries >= max_retries:
             logging.warning("🛑 Max idle retries reached. Ending call.")
             if self.stream_id:
                  async with AsyncSessionLocal() as session:
                      await db_service.log_transcript(session, self.stream_id, "system", f"Call ended by System (Max Idle Retries: {max_retries})", call_db_id=self.call_db_id)
             await self.stop()
             return True

        self.idle_retries += 1
        msg = getattr(self.config, 'idle_message', "¿Hola? ¿Sigue ahí?")
        if msg:
           self.last_interaction_time = now
           await self.speak_direct(msg)
        return False


    async def _send_debug_event(self, event_type: str, data: dict):
        """Helper to send debug events to frontend (Simulator 2.0)."""
        if self.client_type == "browser":
            try:
                msg = {
                    "type": "debug",
                    "event": event_type,
                    "data": data,
                    "timestamp": time.time()
                }
                await self.transport.send_json(msg)
            except Exception:
                pass

    async def start(self) -> None:
        logger.info("🚀 [ORCHESTRATOR] Starting...")
        self.loop = asyncio.get_running_loop()
        
        # STEP 1: Load Configuration
        try:
            await self._load_config()
            
            # Initialize CRM Manager after config is loaded
            from app.core.managers import CRMManager
            self.crm_manager = CRMManager(self.config, self.initial_context_data)
            
        except Exception as e:
            logger.error(f"❌ [ORCHESTRATOR] Config Load Failed: {e}")
            await self.stop()
            return
        
        # STEP 1.5: Fetch CRM Context (Using CRMManager)
        if self.crm_manager:
            try:
                phone = self.initial_context_data.get('from') or self.initial_context_data.get('From')
                await self.crm_manager.fetch_context(phone)
                logger.info("✅ [ORCHESTRATOR] CRM context fetched via CRMManager")
            except Exception as e:
                logger.warning(f"⚠️ [ORCHESTRATOR] CRM Fetch Failed (Non-Blocking): {e}")
        
        # STEP 2: Build Pipeline
        try:
            await self._build_pipeline()
        except Exception as e:
            logger.error(f"❌ [ORCHESTRATOR] Pipeline Build Failed: {e}")
            await self.stop()
            return
        
        # STEP 3: Start Pipeline
        try:
            await self.pipeline.start()
            logger.info("✅ [ORCHESTRATOR] Pipeline Started")
        except Exception as e:
            logger.error(f"❌ [ORCHESTRATOR] Pipeline Start Failed: {e}")
            await self.stop()
            return
        
        # STEP 4: Start Audio Stream (Using AudioManager)
        try:
            await self.audio_manager.start()
            logger.info("✅ [ORCHESTRATOR] AudioManager started")
        except Exception as e:
            logger.error(f"❌ [ORCHESTRATOR] Audio Manager Start Failed: {e}")
            await self.stop()
            return
        
        # STEP 5: Initial Greeting (If Configured)
        greeting_enabled = getattr(self.config, 'greeting_enabled', False)
        greeting_text = getattr(self.config, 'greeting_text', '')
        if greeting_enabled and greeting_text:
            logger.info("👋 [ORCHESTRATOR] Sending Greeting")
            await self.pipeline.push_frame(TextFrame(text=greeting_text))
        
        # STEP 6: Start Idle Monitor
        self.monitor_task = asyncio.create_task(self.monitor_idle())
        
        logger.info("🚀 [ORCHESTRATOR] All Subsystems Running")



    async def stop(self) -> None:
        logger.info("🛑 [ORCHESTRATOR] Stopping...")
        
        if self.pipeline:
            await self.pipeline.stop()
            
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
                
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
                
        # Close DB Record
        
        # --- CRM UPDATE ---
        await self._update_crm_status("Call Ended")
        
        # --- WEBHOOK REPORT ---
        # Fire and forget? Or await? Await to ensure delivery before process death.
        await self._send_webhook_report("Call Ended")
        # ----------------------

        if self.call_db_id:
             try:
                 async with AsyncSessionLocal() as session:
                     await db_service.end_call(session, self.call_db_id)
             except Exception:
                 pass

    # --- INPUT HANDLING (From Routes) ---

    async def process_audio(self, payload: str) -> None:
        """
        Receives Base64 audio from WebSocket (Routes).
        Decodes and pushes to Pipeline.
        """
        if not self.pipeline:
            return

        try:
            # 1. Decode
            audio_bytes = self._decode_audio_payload(payload)
            if not audio_bytes:
                return
                
            # 2. Push to Pipeline
            # 8000Hz PCM 16-bit Mono is standard for telephony, but Browser is 16kHz
            sr = 16000 if self.client_type == "browser" else 8000
            await self.pipeline.queue_frame(AudioFrame(data=audio_bytes, sample_rate=sr, channels=1))
            
        except Exception as e:
            logger.error(f"Error processing audio input: {e}")

    async def handle_interruption(self, text: str = "") -> None:
        """
        Callback for EXTERNAL interruptions (e.g. Client-side VAD).
        Pushes CancelFrame to pipeline.
        """
        logger.warning(f"⚡ [INTERRUPT] Reason: {text}")
        await self._send_debug_event("interruption", {"reason": text})
        
        if self.pipeline:
             await self.pipeline.queue_frame(CancelFrame(reason=text))
             
        # Clear Output Buffers
        await self._clear_output()

    def update_vad_stats(self, rms: float) -> None:
        """Routes listener for VAD stats (Legacy, but useful for metrics)."""
        # We broadcast VAD stats for the Visualizer
        # Note: Ideally this is async, but this hook is currently sync in routes logic.
        # We can fire-and-forget a task if loop exists.
        if self.client_type == "browser" and self.loop:
             asyncio.run_coroutine_threadsafe(self._send_debug_event("vad_level", {"rms": rms}), self.loop)

        """Routes listener for VAD stats (Legacy, but useful for metrics)."""
        # We can push this as metadata or MetricsFrame, or ignore if using Silero.
        # Let's ignore for now to keep it lightweight.
        # Let's ignore for now to keep it lightweight.
        pass

    async def _send_transcript(self, role: str, text: str):
        """Callback for TranscriptReporter."""
        if self.client_type == "browser":
             try:
                 msg = {
                     "type": "transcript",
                     "role": role,
                     "text": text
                 }
                 await self.transport.send_json(msg)
             except Exception:
                 pass

    # --- OUTPUT HANDLING (Transport) ---

    async def send_audio_chunked(self, audio_data: bytes) -> None:
        """
        Splits audio into chunks to allow mixing and pacing.
        """
        # Indicate Speaking State
        if not self.is_bot_speaking:
            self.is_bot_speaking = True
            logger.info("🔊 [ORCHESTRATOR] Bot started speaking")
            
            # Initial Latency (Configurable Pacing)
            # Initial Latency (Configurable Pacing) - "Turn-Taking Delay"
            pacing_ms = getattr(self.config, 'voice_pacing_ms', 500) # Default to 500ms if 0
            if pacing_ms > 0:
                 logger.info(f"⏳ [ORCHESTRATOR] Pacing Delay: {pacing_ms}ms")
                 await asyncio.sleep(pacing_ms / 1000.0)

        # Chunk Calculation
        # Browser: 16kHz 16-bit Mono = 32000 bytes/sec. 20ms = 640 bytes.
        # Telephony: 8kHz 8-bit A-Law = 8000 bytes/sec. 20ms = 160 bytes.
        
        chunk_size = 640 if self.client_type == "browser" else 160
        
        # Enqueue chunks
        for i in range(0, len(audio_data), chunk_size):
            self.audio_queue.put_nowait(audio_data[i : i + chunk_size])

    async def _audio_stream_loop(self):
        """
        Audio Transport Loop. 
        - Mixes Background Audio.
        - Sends to Transport.
        - Handles Timing (Burst for Browser, Paced for Telephony).
        """
        try:
             while True:
                 loop_start = time.time()
                 
                 # 1. Fetch TTS Chunk
                 chunk = None
                 try:
                     chunk = self.audio_queue.get_nowait()
                 except asyncio.QueueEmpty:
                     pass
                 
                 # 2. Prepare Background Chunk (Match TTS duration or default 20ms)
                 # If we have a TTS chunk, strict match. If idle, default frame.
                 needed_len = len(chunk) if chunk else (640 if self.client_type == "browser" else 160)
                 bg_chunk = self._get_next_background_chunk(needed_len)
                 
                 # 3. Mixing & Sending
                 if chunk or bg_chunk:
                      final_chunk = self._mix_audio(chunk, bg_chunk)
                      if final_chunk:
                          # Send directly
                          try:
                              sr = 16000 if self.client_type == "browser" else 8000
                              await self.transport.send_audio(final_chunk, sr)
                          except Exception as e_send:
                              logger.warning(f"Transport send failed: {e_send}")

                 # 4. Timing / Sleep
                 # Plan 1: Browser uses Jitter Buffer, so we can BURST Send TTS.
                 # Only sleep if we are IDLE (generating BG noise) or Telephony (Real-time).
                 
                 if self.client_type == "browser" and chunk:
                     # Burst Mode: Process efficiently but throttle slightly to prevent Client Buffer bloat
                     # 5ms Sleep = Max 200 chunks/sec = 4x Realtime (good balance)
                     await asyncio.sleep(0.005) 
                 else:
                     # Real-time Pacing (Telephony or Idle Background)
                     elapsed = time.time() - loop_start
                     delay = 0.02 - elapsed
                     if delay > 0:
                         await asyncio.sleep(delay)
                     
        except asyncio.CancelledError:
            pass
        except Exception as e_loop:
            logger.error(f"Stream Loop Crash: {e_loop}")

    # --- RESTORED METHODS (Missing from previous refactor) ---

    async def interrupt_speaking(self):
        """
        Called when user barge-in is detected.
        Stops current audio playback and clears queues.
        """
        if self.is_bot_speaking:
            logger.info("🛑 [ORCHESTRATOR] Interruption Detected! Stopping audio.")
            self.is_bot_speaking = False
            
            # Clear Orchestrator Queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except:
                    pass

    async def speak_direct(self, text: str):
        """Helper to make the bot speak (e.g. First Message)."""
        if not self.pipeline:
            return
            
        tts_proc = next((p for p in self.pipeline._processors if isinstance(p, TTSProcessor)), None)
        if tts_proc:
            # Inject directly into TTS
            logger.info(f"🗣️ [ORCHESTRATOR] speak_direct: Injecting '{text}' into TTS...")
            
            # CRITICAL FIX: Manually report transcript for Greeting
            await self._send_transcript("assistant", text)
            
            await tts_proc.process_frame(TextFrame(text=text), direction=1)
        else:
            logger.error("❌ [ORCHESTRATOR] speak_direct: TTS Processor not found in pipeline!")

    async def _load_config(self):
         async with AsyncSessionLocal() as session:
             self.config = await db_service.get_agent_config(session)
             
             # --- APPLY DYNAMIC PACING ---
             pacing = getattr(self.config, 'conversation_pacing', 'moderate')
             
             if pacing == 'fast':
                 self.config.voice_pacing_ms = 0      # Instant response
                 self.config.silence_timeout_ms = 400 # Quick turn-taking
             elif pacing == 'moderate':
                 self.config.voice_pacing_ms = 200    # Natural pause
                 self.config.silence_timeout_ms = 800 # Standard
             elif pacing == 'relaxed':
                 self.config.voice_pacing_ms = 600    # Thoughtful pause
                 self.config.silence_timeout_ms = 1500 # Patient listener

    def _init_providers(self):
        self.llm_provider = ServiceFactory.get_llm_provider(self.config)
        self.stt_provider = ServiceFactory.get_stt_provider(self.config)
        self.tts_provider = ServiceFactory.get_tts_provider(self.config)

    async def _build_pipeline(self):
        # Inject client context into config for processors
        if self.config:
             try:
                 setattr(self.config, 'client_type', self.client_type)
             except Exception:
                 pass 

        # 1. STT
        stt = STTProcessor(self.stt_provider, self.config, self.loop)
        await stt.initialize()
        
        # 2. VAD
        vad = VADProcessor(self.config)
        
        # 3. Aggregator
        agg = ContextAggregator(self.config, self.conversation_history, llm_provider=self.llm_provider)
        
        # 4. LLM
        llm = LLMProcessor(self.llm_provider, self.config, self.conversation_history, context=self.initial_context_data)
        
        # 5. TTS
        tts = TTSProcessor(self.tts_provider, self.config)
        await tts.initialize()
        
        # 6. Metrics
        metrics = MetricsProcessor(self.config)
        
        # 7. Sink
        sink = PipelineOutputSink(self)
        
        # 8. Reporters
        user_reporter = TranscriptReporter(callback=self._send_transcript, role_label="user")
        bot_reporter = TranscriptReporter(callback=self._send_transcript, role_label="assistant")
        
        self.pipeline = Pipeline([stt, vad, user_reporter, agg, llm, bot_reporter, tts, metrics, sink])

    def _load_background_audio(self) -> None:
        """Loads background audio (WAV) and resamples to match output rate."""
        bg_sound = getattr(self.config, 'background_sound', 'none')
        if bg_sound and bg_sound.lower() != 'none':
             try:
                 import pathlib
                 import wave
                 import numpy as np
                 import struct
                 
                 sound_path = pathlib.Path(f"app/static/sounds/{bg_sound}.wav")
                 target_rate = 16000 if self.client_type == 'browser' else 8000

                 if sound_path.exists():
                     logging.info(f"🎵 [BG-SOUND] Loading {sound_path} for target rate {target_rate}Hz...")
                     
                     data = None
                     orig_rate = 44100 
                     
                     try:
                         with wave.open(str(sound_path), "rb") as wf:
                             params = wf.getparams()
                             raw_frames = wf.readframes(params.nframes)
                             orig_rate = params.framerate
                             width = params.sampwidth
                             channels = params.nchannels
                             
                             if width == 2:
                                 data = np.frombuffer(raw_frames, dtype=np.int16)
                             elif width == 1:
                                 data_u8 = np.frombuffer(raw_frames, dtype=np.uint8)
                                 data = (data_u8.astype(np.int16) - 128) * 256
                     except wave.Error:
                         logging.info("♻️ [BG-SOUND] 'wave' failed. Attempting manual decode...")
                         with open(sound_path, "rb") as f:
                             raw_bytes = f.read()
                         try:
                             audio_fmt = struct.unpack('<H', raw_bytes[20:22])[0]
                             channels = struct.unpack('<H', raw_bytes[22:24])[0]
                             orig_rate = struct.unpack('<I', raw_bytes[24:28])[0]
                             data_start = raw_bytes.find(b'data')
                             if data_start != -1:
                                 raw_data = raw_bytes[data_start+8:]
                                 if audio_fmt == 6: 
                                     lin_bytes = AudioProcessor.alaw2lin(raw_data, 2)
                                     data = np.frombuffer(lin_bytes, dtype=np.int16)
                                 elif audio_fmt == 7: 
                                     lin_bytes = AudioProcessor.ulaw2lin(raw_data, 2)
                                     data = np.frombuffer(lin_bytes, dtype=np.int16)
                                 elif audio_fmt == 1:
                                     data = np.frombuffer(raw_data, dtype=np.int16)
                         except Exception:
                             pass

                     if data is not None:
                         if channels == 2 and len(data.shape) > 1:
                             if len(data) % 2 == 0:
                                 data = data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                         elif channels == 2:
                             try:
                                 data = data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                             except:
                                 pass

                         if orig_rate != target_rate:
                             duration = len(data) / orig_rate
                             target_len = int(duration * target_rate)
                             x_old = np.linspace(0, duration, len(data))
                             x_new = np.linspace(0, duration, target_len)
                             data = np.interp(x_new, x_old, data).astype(np.int16)

                         self.bg_loop_buffer = data.tobytes()
                         logging.info(f"🎵 [BG-SOUND] Buffer Ready. Size: {len(self.bg_loop_buffer)}")
                 else:
                     logging.warning(f"⚠️ [BG-SOUND] File not found: {sound_path}")
             except Exception as e_bg:
                 logging.error(f"❌ [BG-SOUND] Unhandled error: {e_bg}")

    def _get_next_background_chunk(self, req_len: int) -> bytes | None:
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
            try:
                bg_lin = bg_chunk 

                if self.client_type == 'browser':
                    tts_lin = tts_chunk
                elif self.client_type == 'telnyx':
                    tts_lin = AudioProcessor.alaw2lin(tts_chunk, 2)
                else:
                    tts_lin = AudioProcessor.ulaw2lin(tts_chunk, 2)

                bg_lin_quiet = AudioProcessor.mul(bg_lin, 2, 0.15)
                mixed_lin = AudioProcessor.add(tts_lin, bg_lin_quiet, 2)

                if self.client_type == 'browser':
                    return mixed_lin
                elif self.client_type == 'telnyx':
                    return AudioProcessor.lin2alaw(mixed_lin, 2)
                else:
                    return AudioProcessor.lin2ulaw(mixed_lin, 2)
            except Exception as e_mix:
                logging.error(f"Mixing error: {e_mix}")
                return tts_chunk 

        elif tts_chunk:
            return tts_chunk

        elif bg_chunk:
             try:
                bg_lin = bg_chunk
                bg_lin_quiet = AudioProcessor.mul(bg_lin, 2, 0.15) 
                
                if self.client_type == 'browser':
                    return bg_lin_quiet
                elif self.client_type == 'telnyx':
                    return AudioProcessor.lin2alaw(bg_lin_quiet, 2)
                else:
                    return AudioProcessor.lin2ulaw(bg_lin_quiet, 2)
             except Exception:
                return None
        return None

    async def _clear_output(self):
        """Clears audio queue and notifies client."""
        # 1. Empty Queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break
        
        # 2. Send Clear Event
        try:
             msg = {"event": "clear"}
             if self.stream_id:
                 msg["streamSid"] = self.stream_id
             await self.transport.send_json(msg)
        except:
            pass
            
    def _decode_audio_payload(self, payload: str) -> Optional[bytes]:
        try:
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += '=' * (4 - missing_padding)
            audio_bytes = base64.b64decode(payload)
            
            # Transcoding Logic (Legacy Support)
            # Assuming Telnyx PCMA/PCMU needed conversion to Linear PCM
            # app/core/audio_processor.py
            
            if self.client_type in ["twilio", "telnyx"]:
                 if self.audio_encoding == 'PCMA':
                     return AudioProcessor.alaw2lin(audio_bytes, 2)
                 else:
                     return AudioProcessor.ulaw2lin(audio_bytes, 2)
            
            return audio_bytes # Browser (Linear/WAV usually)
        except Exception:
            return None

    def _apply_profile_overlay(self):
        """
        Maps provider-specific config fields (Phone/Telnyx) over the base fields
        in the in-memory config object. This ensures Processors use the correct values.
        """
        if not self.config:
            return

        c = self.config
        mode = self.client_type # twilio, telnyx, browser

        if mode == 'browser':
            return # Base config is already Browser

        # Mapping Strategy: Source Suffix -> Target Base
        # We overlay values if they exist
        
        suffix = ""
        if mode == 'twilio':
            suffix = "_phone"
        elif mode == 'telnyx':
            suffix = "_telnyx"
        
        if not suffix:
            return

        logger.info(f"🎭 [CONFIG] Applying Overlay for profile: {mode} (suffix: {suffix})")

        # List of fields to overlay
        fields = [
            # LLM
            ('llm_provider', 'llm_provider'),
            ('llm_model', 'llm_model'),
            ('temperature', 'temperature'),
            ('system_prompt', 'system_prompt'), # Special handling for None?
            ('max_tokens', 'max_tokens'),
            ('first_message', 'first_message'),
            ('first_message_mode', 'first_message_mode'),
            
            # TTS
            ('tts_provider', 'tts_provider'),
            ('voice_language', 'voice_language'),
            ('voice_name', 'voice_name'),
            ('voice_style', 'voice_style'),
            ('voice_speed', 'voice_speed'),
            ('voice_pitch', 'voice_pitch'),
            ('voice_volume', 'voice_volume'),
            ('voice_style_degree', 'voice_style_degree'),
            ('background_sound', 'background_sound'),
            ('voice_pacing_ms', 'voice_pacing_ms'),
            
            # STT / Helpers
            ('stt_provider', 'stt_provider'),
            ('stt_language', 'stt_language'),
            ('interruption_threshold', 'interruption_threshold'),
            ('silence_timeout_ms', 'silence_timeout_ms'),
            ('input_min_characters', 'input_min_characters'),
            ('hallucination_blacklist', 'hallucination_blacklist'),
            ('enable_denoising', 'enable_denoising'),
            
            # VAD/Flow
            ('vad_threshold', 'vad_threshold'),
            ('idle_timeout', 'idle_timeout'),
            ('max_duration', 'max_duration'),
            ('idle_message', 'idle_message'),
            
            # Legacy/Specific
            ('initial_silence_timeout_ms', 'initial_silence_timeout_ms'),
            ('voice_sensitivity', 'interruptRMS'), # Telnyx alias check?
        ]
        
        for base_field, _ in fields:
            source_field = f"{base_field}{suffix}"
            
            # Special case for Telnyx native fields that might map differently or strictly exist
            # But our map above assumes simple suffixing. 
            # Let's handle exceptions or special mappings if needed.
            
            if hasattr(c, source_field):
                val = getattr(c, source_field)
                if val is not None:
                     # For prompts, only overwrite if not empty/null? 
                     # DB default is often None for overlays.
                     if "system_prompt" in base_field and not val:
                         continue 
                     
                     # Overwrite base
                     current = getattr(c, base_field, None)
                     setattr(c, base_field, val)
                     # logger.debug(f"   Overwriting {base_field}: {current} -> {val}")
        
        # Telnyx Specifics (Native)
        if mode == 'telnyx':
             # Handled largely by specific processors checking config.enable_krisp_telnyx
             # But generic Processors (VAD) might look at base defaults.
             if hasattr(c, 'voice_sensitivity_telnyx'):
                  setattr(c, 'voice_sensitivity', getattr(c, 'voice_sensitivity_telnyx'))

    # --- CRM INTEGRATION (Baserow) ---
    async def _fetch_crm_context(self):
        """
        Fetches contact details from Baserow and merges into initial_context_data.
        """
        if not self.config or not getattr(self.config, 'crm_enabled', False):
            return

        token = getattr(self.config, 'baserow_token', None)
        table_id = getattr(self.config, 'baserow_table_id', None)

        if not token or not table_id:
            logger.warning("⚠️ [CRM] Enabled but missing token/table_id")
            return

        # Identify Phone Number
        # Different providers use different keys. 
        # Twilio: 'From', Telnyx: 'from' (in sip headers or payload?). 
        # Logic: Check standard keys in initial_context_data
        phone = self.initial_context_data.get('from') or self.initial_context_data.get('From') or self.initial_context_data.get('caller_number')
        
        if not phone and self.client_type == 'simulator':
             # For testing, check if simulated phone provided
             phone = self.initial_context_data.get('phone')

        if not phone:
            logger.info("ℹ️ [CRM] No phone number found in context. Skipping lookup.")
            return

        try:
            from app.services.baserow import BaserowClient
            client = BaserowClient(token)
            
            logger.info(f"🔍 [CRM] Searching Baserow for {phone}...")
            row = await client.find_contact(table_id, phone)
            
            if row:
                logger.info(f"✅ [CRM] Found Context: {row.keys()}")
                # Store Row ID for updates
                self.initial_context_data['baserow_row_id'] = row['id']
                
                # Merge Row Data into Context (Prefixing optional, but merging flat for prompt ease)
                # We prioritize existing keys if overlap? Or CRM?
                # Let's overwrite with CRM data as it's likely more rich/correct.
                self.initial_context_data.update(row)
            else:
                logger.info("ℹ️ [CRM] Contact not found in DB.")
                
        except Exception as e:
            logger.error(f"❌ [CRM] Lookup failed: {e}")

    async def _update_crm_status(self, status: str = "Call Ended"):
        """
        Updates Baserow row with call outcome.
        """
        if not self.config or not getattr(self.config, 'crm_enabled', False):
            return

        row_id = self.initial_context_data.get('baserow_row_id')
        if not row_id:
            return

        token = getattr(self.config, 'baserow_token', None)
        table_id = getattr(self.config, 'baserow_table_id', None)
        
        if not token or not table_id:
            return

        try:
            from app.services.baserow import BaserowClient
            client = BaserowClient(token)
            
            # Construct Update Payload
            # Ideally we have a 'Notes' or 'Last Call Status' field.
            # We map standard fields.
            # Assuming fields: 'Status', 'Last Call', 'Duration'
            
            data = {
                "Status": status,
                # "Last Call": datetime.now().isoformat(), # If field exists
            }
            
            # Add Duration if available
            duration = int(time.time() - self.start_time)
            data["Duration"] = str(duration) # Text or Number depending on schema

            logger.info(f"📝 [CRM] Updating Row {row_id}: {data}")
            await client.update_contact(table_id, row_id, data)
            
        except Exception as e:
            logger.error(f"❌ [CRM] Update failed: {e}")

    # --- WEBHOOK INTEGRATION (Phase 9) ---
    async def _send_webhook_report(self, status: str = "finished"):
        """
        Sends End-of-Call Report to configured Webhook.
        """
        if not self.config or not getattr(self.config, 'webhook_url', None):
            return

        url = self.config.webhook_url
        secret = getattr(self.config, 'webhook_secret', None)
        
        try:
            from app.services.webhook import WebhookService
            service = WebhookService(url, secret)
            
            # Metadata
            duration = int(time.time() - self.start_time)
            meta = {
                "duration_seconds": duration,
                "client_type": self.client_type,
                "status": status,
                "stream_id": self.stream_id,
                "db_call_id": self.call_db_id
            }
            
            # Merge Context (Baserow ID, Campaign, etc.)
            if self.initial_context_data:
                meta.update(self.initial_context_data)
            
            # Analysis (Placeholder for now, could use LLM here later)
            analysis = {
                "success": True if duration > 10 else False,
                "summary": "Call completed successfully."
            }

            logger.info("📡 [WEBHOOK] Triggering Report...")
            await service.send_end_call_report(
                call_id=self.stream_id or str(uuid.uuid4()),
                agent_config_name=getattr(self.config, 'name', 'default'),
                metadata=meta,
                transcript=self.conversation_history, # Full Transcript
                analysis=analysis,
                recording_url=None # TODO: Fetch from Telnyx if available
            )
            
        except Exception as e:
            logger.error(f"❌ [WEBHOOK] Trigger failed: {e}")

