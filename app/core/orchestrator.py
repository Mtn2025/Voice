import asyncio
import audioop
import base64
import contextlib
import io
import json
import logging
import time
import uuid
import wave

from fastapi import WebSocket

from app.core.config import settings  # Required for API Keys
from app.core.service_factory import ServiceFactory
from app.core.vad_filter import AdaptiveInputFilter  # VAD Filter module
from app.services.base import STTEvent, STTResultReason
from app.services.db_service import db_service

# AdaptiveInputFilter moved to app.core.vad_filter
# Import: from app.core.vad_filter import AdaptiveInputFilter


class VoiceOrchestrator:
    def __init__(self, websocket: WebSocket, client_type: str = "twilio"):
        """
        client_type: 'twilio' or 'browser'
        """
        self.websocket = websocket
        self.client_type = client_type
        self.conversation_history = []
        self.is_bot_speaking = False
        self.last_audio_sent_at = 0 # Track when we last sent bytes
        self.stream_id = None
        self.call_db_id = None
        self.config = None
        self.user_audio_buffer = bytearray() # Capture user audio

        # Providers (Initialized in start)
        self.stt_provider = None
        self.llm_provider = None
        self.tts_provider = None

        # Azure Objects
        self.recognizer = None
        self.push_stream = None
        self.synthesizer = None
        self.response_task = None # Track current generation task
        self.monitor_task = None # Track idle monitor task

        # Flow Control State
        self.last_interaction_time = time.time()
        self.start_time = time.time()

        self.was_interrupted = False # Track if last stop was due to interruption

        # Adaptive VAD
        self.vad_filter = AdaptiveInputFilter()

        self.current_turn_max_rms = 0.0

        # Audio Mixing (Background Sound)
        self.bg_loop_buffer = None
        self.bg_loop_index = 0

        # Audio Streaming Queue (Decoupled Output)
        self.audio_queue = asyncio.Queue()
        self.stream_task = None

    async def send_audio_chunked(self, audio_data: bytes):
        """
        PRODUCER: Queues audio chunks for the continuous stream loop.
        Breaks down large TTS buffers into 20ms chunks (160 bytes for telephony).
        """
        if self.client_type == "browser":
             # Browser still uses direct send (for now, or can be unified later)
             # Browser is robust enough for gaps, but unification is cleaner.
             # Keeping legacy path for browser to avoid regression there.
             b64 = base64.b64encode(audio_data).decode("utf-8")
             await self.websocket.send_text(json.dumps({"type": "audio", "data": b64}))
             return

        # For Telephony: Queue slices
        CHUNK_SIZE = 160
        for i in range(0, len(audio_data), CHUNK_SIZE):
            chunk = audio_data[i : i + CHUNK_SIZE]
            self.audio_queue.put_nowait(chunk)

    async def _audio_stream_loop(self):
        """
        CONSUMER: Continuous 20ms Loop.
        Mixes Background Audio + TTS Queue -> Socket.
        Ensures constant stream (Carrier) to keep line alive and ambiance smooth.
        """
        logging.info("🌊 [STREAM] Starting Continuous Audio Stream Loop")
        try:
            while True:
                # 1. TIMING: Target 20ms (0.02s)
                loop_start = asyncio.get_running_loop().time()

                # 2. FETCH TTS (Non-blocking)
                tts_chunk = None
                with contextlib.suppress(asyncio.QueueEmpty):
                    tts_chunk = self.audio_queue.get_nowait()

                # 3. FETCH BACKGROUND (If connected)
                bg_chunk = None
                if self.bg_loop_buffer and len(self.bg_loop_buffer) > 0:
                     # Calculate needed size (default 160)
                     req_len = 160
                     if tts_chunk:
                         req_len = len(tts_chunk)

                     if self.bg_loop_index + req_len > len(self.bg_loop_buffer):
                        part1 = self.bg_loop_buffer[self.bg_loop_index:]
                        remaining = req_len - len(part1)
                        part2 = self.bg_loop_buffer[:remaining]
                        bg_chunk = part1 + part2
                        self.bg_loop_index = remaining
                     else:
                        bg_chunk = self.bg_loop_buffer[self.bg_loop_index : self.bg_loop_index + req_len]
                        self.bg_loop_index += req_len

                # 4. MIXING LOGIC
                final_chunk = None

                if tts_chunk and bg_chunk:
                    # MIX
                    try:
                        bg_lin = audioop.alaw2lin(bg_chunk, 2)

                        if self.client_type == 'telnyx':
                            tts_lin = audioop.alaw2lin(tts_chunk, 2)
                        else:
                            tts_lin = audioop.ulaw2lin(tts_chunk, 2)

                        bg_lin_quiet = audioop.mul(bg_lin, 2, 0.15)
                        mixed_lin = audioop.add(tts_lin, bg_lin_quiet, 2)

                        if self.client_type == 'telnyx':
                            final_chunk = audioop.lin2alaw(mixed_lin, 2)
                        else:
                            final_chunk = audioop.lin2ulaw(mixed_lin, 2)
                    except Exception as e_mix:
                        logging.error(f"Mixing error: {e_mix}")
                        final_chunk = tts_chunk # Fallback

                elif tts_chunk:
                    final_chunk = tts_chunk

                elif bg_chunk:
                    # JUST BACKGROUND (Silence filling)
                    # Must be careful not to send too much if socket is buffering,
                    # but typically we drive this.
                    try:
                        bg_lin = audioop.alaw2lin(bg_chunk, 2)
                        bg_lin_quiet = audioop.mul(bg_lin, 2, 0.15) # Quiet BG

                        if self.client_type == 'telnyx':
                            final_chunk = audioop.lin2alaw(bg_lin_quiet, 2)
                        else:
                            final_chunk = audioop.lin2ulaw(bg_lin_quiet, 2)
                    except:
                        pass

                # 5. SEND (If we have something to send)
                if final_chunk:
                    b64_audio = base64.b64encode(final_chunk).decode("utf-8")
                    msg = {
                        "event": "media",
                        "media": {"payload": b64_audio}
                    }
                    if self.client_type == "twilio":
                        msg["streamSid"] = self.stream_id
                    elif self.client_type == "telnyx":
                        msg["stream_id"] = self.stream_id

                    try:
                        await self.websocket.send_text(json.dumps(msg))
                    except Exception:
                        break # Socket closed?

                # 6. SLEEP (Maintain 20ms cadence)
                elapsed = asyncio.get_running_loop().time() - loop_start
                delay = 0.02 - elapsed
                if delay > 0:
                    await asyncio.sleep(delay)
                else:
                    # Running behind, yield briefly
                    await asyncio.sleep(0)

        except asyncio.CancelledError:
             logging.info("🌊 [STREAM] Loop Cancelled")
        except Exception as e_loop:
             logging.error(f"🌊 [STREAM] Loop Crash: {e_loop}")

    def _synthesize_text(self, text):
        """
        Wraps text in SSML with configured voice and style, respecting client_type.
        """
        # Default to Browser/Simulator settings
        voice = getattr(self.config, 'voice_name', 'es-MX-DaliaNeural')
        style = getattr(self.config, 'voice_style', None)
        speed = getattr(self.config, 'voice_speed', 1.0)

        # Override for Twilio
        if self.client_type == 'twilio':
            voice = getattr(self.config, 'voice_name_phone', voice)
            style = getattr(self.config, 'voice_style_phone', style)
            speed = getattr(self.config, 'voice_speed_phone', 0.9)

        # Override for Telnyx
        elif self.client_type == 'telnyx':
            voice = getattr(self.config, 'voice_name_telnyx', voice)
            style = getattr(self.config, 'voice_style_telnyx', style)
            speed = getattr(self.config, 'voice_speed_telnyx', 0.9) # Default to 0.9 if missing

        # Manual Override (Generic) - Check if this should apply to all or just browser?
        # Assuming manual override is for testing/browser primarily, but let's leave it generic if set.
        if getattr(self.config, 'voice_id_manual', None):
             voice = self.config.voice_id_manual

        # Build SSML
        ssml_parts = [
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" ',
            'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-MX">',
            f'<voice name="{voice}">'
        ]

        # Open Prosody (Speed)
        ssml_parts.append(f'<prosody rate="{speed}">')

        if style and style.strip():
            ssml_parts.append(f'<mstts:express-as style="{style}">')
            ssml_parts.append(text)
            ssml_parts.append('</mstts:express-as>')
        else:
            ssml_parts.append(text)

        # Close Prosody
        ssml_parts.append('</prosody>')

        ssml_parts.append('</voice></speak>')

        ssml = "".join(ssml_parts)
        ssml = "".join(ssml_parts)
        # Assuming synthesizer is set up
        if not self.synthesizer:
            logging.error("Synthesizer not initialized in _synthesize_text")
            return None

        # Abstracted TTS call
        return await self.tts_provider.synthesize_ssml(self.synthesizer, ssml)

    def update_vad_stats(self, rms: float):
        """Called by routes.py when client sends VAD stats."""
        # Update self-calibration profile
        self.vad_filter.update_profile(rms)
        self.current_turn_max_rms = rms
        logging.info(f"📊 [VAD STATS] RMS: {rms:.4f} | Avg: {self.vad_filter.avg_rms:.4f} | Samples: {self.vad_filter.samples}")

    async def speak_direct(self, text: str):
        """Helper to speak text without LLM generation (e.g. Idle messages)"""
        if not text:
            return
        self.is_bot_speaking = True
        try:
            # We must run blocking sync calls in executor if TTS is blocking, but assume async here or fast enough
            # For Azure, synthesize_stream is wrapped or we use simple one-off
            # We implemented synthesize_stream as async in AbstractTTS?
            # Let's check AzureProvider.synthesize_stream. It uses `speak.speak_text_async`.
            # We need to verify if we get bytes easily.
            # Ideally we reuse the existing TTS path but it's buried in generate_response.
            # I will assume `synthesize_stream` returns bytes.

            # Note: The current Azure implementation in Orchestrator `generate_response` uses direct SDK calls unfortunately
            # instead of the Provider abstraction fully. This is debt.
            # I will use the `tts_provider.synthesize_stream` if available, or copy logic.
            # Logic in generate_response: "result = synthesizer.speak_text_async(text_chunk).get()"

            # Simple fallback for now:
            if self.synthesizer:
                asyncio.get_running_loop()
                # Use SSML helper
                # Use SSML helper
                audio_data = await self.tts_provider.synthesize_ssml(self.synthesizer, self._synthesize_text_ssml_only(text))
                if audio_data:
                     await self.send_audio_chunked(audio_data)

            # Log
            self.conversation_history.append({"role": "assistant", "content": text})
            if self.stream_id:
               logging.info(f"💾 [LOG-DB] ASSISTANT: {text}")
               await db_service.log_transcript(self.stream_id, "assistant", text + " [IDLE]", call_db_id=self.call_db_id)

        except Exception as e:
            logging.error(f"Idle/Direct output error: {e}")
        finally:
            self.last_interaction_time = time.time()
            # For Browser, wait for speech_ended
            # For Browser, wait for speech_ended
            # For Twilio, we assume immediate completion (or handle differently)
            if self.client_type.lower() != "browser":
                self.is_bot_speaking = False
            else:
                 logging.info("🕒 [BROWSER] Waiting for speech_ended (Response Task Done).")

    async def monitor_idle(self):
        logging.warning("🏁 [MONITOR] Starting monitor_idle loop...")
        while True:
            await asyncio.sleep(1.0)
            logging.warning("⏰ [MONITOR] Tick.")
            try:
                now = time.time()

                # Max Duration Check
                max_dur = getattr(self.config, 'max_duration', 600)
                if now - self.start_time > max_dur:
                     logging.info("🛑 Max duration reached. Ending call.")
                     if self.stream_id:
                         async with AsyncSessionLocal() as session:
                             await db_service.log_transcript(session, self.stream_id, "system", "Call ended by System (Max Duration Reached)", call_db_id=self.call_db_id)
                     if self.client_type == "browser":
                         await self.websocket.close()
                     break

                # Idle Check (Only if not speaking)
                idle_timeout = getattr(self.config, 'idle_timeout', 10.0)
                idle_timeout = getattr(self.config, 'idle_timeout', 10.0)
                logging.warning(f"🔍 [IDLE-CHECK] Speaking: {self.is_bot_speaking} | Elapsed: {now - self.last_interaction_time:.2f}s | StartDelta: {now - self.start_time:.2f}")

                if not self.is_bot_speaking and (now - self.last_interaction_time > idle_timeout):
                     if not hasattr(self, 'idle_retries'):
                         self.idle_retries = 0

                     max_retries = getattr(self.config, 'inactivity_max_retries', 3)
                     logging.warning(f"zzz Idle timeout reached. Retry {self.idle_retries + 1}/{max_retries}")

                     if self.idle_retries >= max_retries:
                         logging.warning("🛑 Max idle retries reached. Ending call.")
                         # Optional: Goodbye message for inactivity?
                         # await self.speak_direct("Parece que no me escuchas. Colgaré por ahora.")
                         # For now, just end it to save cost as requested.
                         if self.client_type == "browser":
                             await self.websocket.close()
                         elif self.client_type == "telnyx":
                              # Should trigger end call hook
                              pass

                         # Ensure we break loop and cleanup
                         if self.stream_id:
                             await db_service.log_transcript(self.stream_id, "system", f"Call ended by System (Max Idle Retries: {max_retries})", call_db_id=self.call_db_id)

                         # Trick to force close: Cancel myself? Or just break?
                         # If we break, we exit monitor, but main server keeps socket open?
                         # Best is to signal stop.
                         # self.stop() is async but we are in async loop.
                         # We should probably raise an event or close socket.
                         await self.websocket.close() # This usually kills the connection handler
                         break

                     self.idle_retries += 1
                     msg = getattr(self.config, 'idle_message', "¿Hola? ¿Sigue ahí?")
                     if msg:
                        self.last_interaction_time = now # Reset to wait again
                        asyncio.create_task(self.speak_direct(msg))

            except Exception as e:
                 logging.warning(f"Monitor error: {e}")

    async def start(self):
        logging.warning("🦄🦄🦄 CANARY TEST: SI ESTO SALE, EL CODIGO ES NUEVO 🦄🦄🦄")
        logging.warning(f"DEBUG CLIENT_TYPE: self.client_type = '{self.client_type}'")
        # ... (no change to start) ...
        #from app.services.db_service import db_service
        from app.db.database import AsyncSessionLocal  # NEW

        # Capture the current event loop to schedule tasks from sync callbacks
        self.loop = asyncio.get_running_loop()

        # Load Config
        try:
            logging.warning("⚙️ [CONFIG] Attempting to load agent config from DB...")
            async with AsyncSessionLocal() as session:
                self.config = await db_service.get_agent_config(session)
            logging.warning(f"✅ [CONFIG] Loaded successfully: {type(self.config)}")
            logging.info(f"DEBUG CONFIG TYPE: {type(self.config)}")
            logging.info(f"DEBUG CONFIG VAL: {self.config}")
        except Exception as e:
            logging.error(f"❌❌❌ CRITICAL: Config loading failed: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            raise

        logging.warning("🎯 [TRACE] Config loaded, starting profile overlay...")
        # ---------------- PROFILE OVERLAY (PHONE / TELNYX) ----------------
        # ---------------- PROFILE OVERLAY (PHONE / TELNYX) ----------------
        logging.warning(f"🔍 [TRACE] About to check client_type condition: '{self.client_type}' == 'telnyx' ? {self.client_type == 'telnyx'}")
        if self.client_type == "telnyx":
             try:
                  logging.warning("📱 [TELNYX] ENTERED Telnyx profile overlay block")
                  logging.warning("📱 [ORCHESTRATOR] Applying TELNYX Profile Configuration")
                  # Explicitly map TELNYX fields
                  conf = self.config

                  # LLM
                  if conf.llm_model_telnyx:
                      conf.llm_model = conf.llm_model_telnyx
                  if conf.llm_provider_telnyx:
                      conf.llm_provider = conf.llm_provider_telnyx
                  if conf.system_prompt_telnyx:
                      conf.system_prompt = conf.system_prompt_telnyx
                  if conf.max_tokens_telnyx:
                      conf.max_tokens = conf.max_tokens_telnyx
                  if conf.first_message_telnyx:
                      conf.first_message = conf.first_message_telnyx
                  if conf.first_message_mode_telnyx:
                      conf.first_message_mode = conf.first_message_mode_telnyx
                  if conf.temperature_telnyx is not None:
                      conf.temperature = conf.temperature_telnyx

                  # VAD / Audio IN
                  if conf.stt_provider_telnyx:
                      conf.stt_provider = conf.stt_provider_telnyx
                  if conf.stt_language_telnyx:
                      conf.stt_language = conf.stt_language_telnyx
                  if conf.silence_timeout_ms_telnyx:
                      conf.silence_timeout_ms = conf.silence_timeout_ms_telnyx
                  if conf.initial_silence_timeout_ms_telnyx:
                      conf.initial_silence_timeout_ms = conf.initial_silence_timeout_ms_telnyx
                  if conf.interruption_threshold_telnyx is not None:
                      conf.interruption_threshold = conf.interruption_threshold_telnyx
                  if conf.input_min_characters_telnyx:
                      conf.input_min_characters = conf.input_min_characters_telnyx
                  if conf.enable_denoising_telnyx is not None:
                      conf.enable_denoising = conf.enable_denoising_telnyx
                  if conf.hallucination_blacklist_telnyx:
                      conf.hallucination_blacklist = conf.hallucination_blacklist_telnyx
                  if conf.voice_sensitivity_telnyx:
                      conf.voice_sensitivity = conf.voice_sensitivity_telnyx
                  if conf.enable_vad_telnyx is not None:
                      conf.enable_vad = conf.enable_vad_telnyx
                  if conf.enable_krisp_telnyx is not None:
                      conf.enable_krisp = conf.enable_krisp_telnyx

                  # Voice / Audio OUT
                  if conf.voice_name_telnyx:
                      conf.voice_name = conf.voice_name_telnyx
                  if conf.voice_style_telnyx:
                      conf.voice_style = conf.voice_style_telnyx
                  if conf.voice_speed_telnyx:
                      conf.voice_speed = conf.voice_speed_telnyx
                  if conf.voice_pacing_ms_telnyx:
                      conf.voice_pacing_ms = conf.voice_pacing_ms_telnyx

                  # Functions (Transfer / Keypad)
                  if conf.transfer_phone_number:
                      conf.transfer_phone_number = conf.transfer_phone_number
                  # Note: enable_dial_keypad is global, but we can override if needed.
                  # For now, we assume if it's set in dashboard it applies.

                  # Flow Control Overrides (Independent Timeouts)
                  # If set in DB (and not None/0.0 if default logic differs), apply.
                  # Since default is 20.0, we just trust the DB value.
                  if conf.idle_timeout_telnyx is not None:
                      conf.idle_timeout = conf.idle_timeout_telnyx
                  if conf.max_duration_telnyx is not None:
                      conf.max_duration = conf.max_duration_telnyx
                  if conf.idle_message_telnyx:
                      conf.idle_message = conf.idle_message_telnyx

                  logging.warning("✅ [TELNYX] Profile overlay completed successfully")
             except Exception as e:
                  logging.error(f"❌❌❌ EXCEPTION in Telnyx profile overlay: {e}")
                  import traceback
                  logging.error(f"Traceback: {traceback.format_exc()}")


        elif self.client_type == "twilio" or (self.client_type not in ("browser", "telnyx")):
             # Default fallback for "phone" matches Twilio behavior
             logging.info("📱 [ORCHESTRATOR] Applying TWILIO/PHONE Profile Configuration")
             conf = self.config

             # LLM
             if conf.llm_model_phone:
                 conf.llm_model = conf.llm_model_phone
             if conf.llm_provider_phone:
                 conf.llm_provider = conf.llm_provider_phone
             if conf.system_prompt_phone:
                 conf.system_prompt = conf.system_prompt_phone
             if conf.max_tokens_phone:
                 conf.max_tokens = conf.max_tokens_phone
             if conf.first_message_phone:
                 conf.first_message = conf.first_message_phone
             if conf.first_message_mode_phone:
                 conf.first_message_mode = conf.first_message_mode_phone
             if conf.temperature_phone is not None:
                 conf.temperature = conf.temperature_phone

             # VAD / Audio IN
             if conf.stt_provider_phone:
                 conf.stt_provider = conf.stt_provider_phone
             if conf.stt_language_phone:
                 conf.stt_language = conf.stt_language_phone
             if conf.silence_timeout_ms_phone:
                 conf.silence_timeout_ms = conf.silence_timeout_ms_phone
             if conf.initial_silence_timeout_ms_phone:
                 conf.initial_silence_timeout_ms = conf.initial_silence_timeout_ms_phone
             if conf.interruption_threshold_phone is not None:
                 conf.interruption_threshold = conf.interruption_threshold_phone
             if conf.input_min_characters_phone:
                 conf.input_min_characters = conf.input_min_characters_phone
             if getattr(conf, 'enable_denoising_phone', None) is not None:
                 conf.enable_denoising = conf.enable_denoising_phone
             if getattr(conf, 'hallucination_blacklist_phone', None):
                 conf.hallucination_blacklist = conf.hallucination_blacklist_phone

             # Voice / Audio OUT
             if conf.voice_name_phone:
                 conf.voice_name = conf.voice_name_phone
             if conf.voice_style_phone:
                 conf.voice_style = conf.voice_style_phone
             if conf.voice_speed_phone:
                 conf.voice_speed = conf.voice_speed_phone
             # Note: voice_pacing_ms might not be on phone model yet, check if needed

        if self.client_type != "browser":
             logging.info(f"📱 [PROFILE APPLIED] Client: {self.client_type} | Voice: {self.config.voice_name} | STT: {self.config.stt_provider}")
        # ---------------------------------------------------------
        # ---------------------------------------------------------

        self.conversation_history.append({"role": "system", "content": self.config.system_prompt})

        # BROADCAST CONFIG TO CLIENT (e.g. Background Sound)
        if self.client_type == "browser":
            bgs = getattr(self.config, "background_sound", "none")
            bgs_url = getattr(self.config, "background_sound_url", None)

            await self.websocket.send_text(json.dumps({
                "type": "config",
                "config": {
                    "background_sound": bgs,
                    "background_sound_url": bgs_url
                }
            }))



        # Initialize Providers
        logging.warning("🔧 [TRACE] About to initialize providers (STT/LLM/TTS)...")
        self.llm_provider = ServiceFactory.get_llm_provider(self.config)
        self.stt_provider = ServiceFactory.get_stt_provider(self.config)
        self.tts_provider = ServiceFactory.get_tts_provider(self.config)  # Using Factory abstraction if possible
        logging.warning("✅ [TRACE] Providers initialized successfully")

        # Setup STT (Azure)
        # Note: In a pure abstract world, we'd wrap these events too,
        # but for now we know it's Azure underlying.
        # Configure Timeouts
        silence_timeout = getattr(self.config, 'silence_timeout_ms', 500)
        if self.client_type != "browser":
             silence_timeout = getattr(self.config, 'silence_timeout_ms_phone', 2000)

        logging.warning(f"⚙️ [CONFIG] STT Silence Timeout: {silence_timeout}ms")

        # -----------------------------------------------------
        # LOAD BACKGROUND AUDIO (If enabled)
        # -----------------------------------------------------
        bg_sound = getattr(self.config, 'background_sound', 'none')
        if bg_sound and bg_sound.lower() != 'none' and self.client_type != 'browser':
             try:
                 import os
                 # User clarification: "existe .wav con configuracion a-law"
                 sound_path = f"app/static/sounds/{bg_sound}.wav"

                 if os.path.exists(sound_path):
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
        # -----------------------------------------------------

        self.recognizer = self.stt_provider.create_recognizer(
            language=getattr(self.config, 'stt_language', 'es-MX'),
            audio_mode=self.client_type,
            on_interruption_callback=self.handle_interruption,
            event_loop=self.loop,
            initial_silence_ms=getattr(self.config, 'initial_silence_timeout_ms', 30000),
            segmentation_silence_ms=silence_timeout
        )

        # Wire up Abstraction events
        self.recognizer.subscribe(self.handle_recognition_event)

        # Setup TTS
        self.synthesizer = self.tts_provider.create_synthesizer(voice_name=self.config.voice_name, audio_mode=self.client_type)

        if self.stream_id:
            self.call_db_id = await db_service.create_call(self.stream_id)

        # Start background idle monitor
        # Start background idle monitor
        logging.warning("🚀 [START] Creating monitor_idle task...")
        self.monitor_task = asyncio.create_task(self.monitor_idle())

        # Start Continuous Audio Stream (Telephony)
        if self.client_type != "browser":
             logging.warning("🌊 [START] Launching Audio Stream Loop...")
             self.stream_task = asyncio.create_task(self._audio_stream_loop())

        logging.warning("🚀 [START] Tasks created.")

        # Start Recognition (Async)
        try:
            logging.warning("🎤 [AZURE] Starting Continuous Recognition Async...")
            self.recognizer.start_continuous_recognition_async().get()
            logging.warning("✅ [AZURE] Continuous Recognition Started")
        except Exception as e_rec:
            logging.error(f"❌ [AZURE] Failed to start recognition: {e_rec}")
            raise

        # DIAGNOSTIC: Verify Azure STT state
        logging.warning("🔍 [AZURE-DIAG] Recognizer started successfully")
        logging.warning(f"🔍 [AZURE-DIAG] Language: {getattr(self.config, 'stt_language', 'UNKNOWN')}")
        logging.warning(f"🔍 [AZURE-DIAG] Client type: {self.client_type}")

        # DIAGNOSTIC: Verify Azure STT state
        logging.warning("🔍 [AZURE-DIAG] Recognizer started successfully")
        logging.warning(f"🔍 [AZURE-DIAG] Language: {getattr(self.config, 'stt_language', 'UNKNOWN')}")
        logging.warning(f"🔍 [AZURE-DIAG] Client type: {self.client_type}")


        logging.warning("🎤 [TRACE] About to process first message logic...")
        # First Message Logic (VAPI Style)
        first_mode = getattr(self.config, 'first_message_mode', 'speak-first')
        first_msg = getattr(self.config, 'first_message', "Hola, soy Andrea. ¿En qué puedo ayudarte?")
        logging.warning(f"🎤 [FIRST_MSG] Mode='{first_mode}', Msg='{first_msg}', Check={first_mode == 'speak-first' and bool(first_msg)}")

        if first_mode == 'speak-first' and first_msg:
             logging.warning("🎤 [FIRST_MSG] ✅ CREATING delayed_greeting task...")
             # VOICE CLIENTS (Twilio/Telenyx): Wait for 'start' event to get StreamSid
             # CRITICAL: Run this in background to avoid blocking 'routes.py' loop
             async def delayed_greeting(message: str):
                  try:
                      logging.warning("🔔 [GREETING] Function started")
                      logging.warning(f"🔔 [GREETING] Message to speak: {message}")
                      if self.client_type != "browser":
                          logging.info("⏳ Waiting for Media Stream START event before greeting...")
                          for _ in range(50): # Wait up to 5 seconds
                              if self.stream_id:
                                  logging.info(f"✅ StreamID obtained ({self.stream_id}). Speaking now.")
                                  break
                              await asyncio.sleep(0.1)
                          else:
                              logging.warning("⚠️ Timed out waiting for StreamID. Speaking anyway (might fail).")

                      logging.info(f"🗣️ Triggering First Message: {message}")
                      await self.speak_direct(message)
                  except Exception as e:
                      logging.error(f"❌ Error in delayed_greeting: {e}")
                      import traceback
                      logging.error(f"Traceback: {traceback.format_exc()}")

             # Store task reference to prevent garbage collection and handle errors
             self.greeting_task = asyncio.create_task(delayed_greeting(first_msg))
             logging.warning(f"🎤 [FIRST_MSG] ✅ Task created: {self.greeting_task}")
        elif first_mode == 'speak-first-dynamic':
             # Placeholder for dynamic generation (future)
             pass

    async def stop(self):
        # 1. Cancel Response Task
        if self.response_task:
            self.response_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.response_task
        # 2. Cancel Audio Stream
        if self.stream_task:
            self.stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.stream_task
            self.stream_task = None

        # 3. Cancel Idle Monitor
        if self.monitor_task:
            logging.info("🛑 Cancelling idle monitor...")
            self.monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitor_task
            self.monitor_task = None

        self.response_task = None



        if self.recognizer:
            with contextlib.suppress(Exception):
                self.recognizer.stop_continuous_recognition()

        # TRIGGER DATA EXTRACTION
        if self.call_db_id:
            try:
                # logging.info("🔌 Running Post-Call Analysis...")
                # Construct full transcript for context
                transcript_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history if msg['role'] != 'system'])

                if transcript_text and len(transcript_text) > 10:
                    logging.info("📊 Extracting data from transcript...")
                    # Use configured model for extraction
                    extraction_model = self.config.extraction_model or "llama-3.1-8b-instant"
                    extracted_data = await self.llm_provider.extract_data(transcript_text, model=extraction_model)
                    logging.info(f"✅ Extraction Result: {extracted_data}")
                    async with AsyncSessionLocal() as session:
                        await db_service.update_call_extraction(session, self.call_db_id, extracted_data)
                else:
                    logging.info("⚠️ Transcript too short for extraction.")
            except Exception as e:
                logging.error(f"Post-Call Analysis Failed: {e}")

    def handle_recognizing(self, evt):
        # Reset Idle Timer also on partial speech to avoid interrupting mid-sentence if slow
        self.last_interaction_time = time.time()

    # REMOVED: handle_canceled, handle_session_stopped (handled by generic event logic)

    def handle_recognition_event(self, evt: STTEvent):
        """
        Event handler for Generic STT events (Abstracted).
        """
        logging.warning(f"🎤 [STT EVENT] Reason: {evt.reason} | Text: {evt.text}")

        # Handle Cancellation
        if evt.reason == STTResultReason.CANCELED:
             logging.error(f"❌ STT Canceled: {evt.error_details}")
             return

        # Only process RecognizedSpeech
        if evt.reason == STTResultReason.RECOGNIZED_SPEECH:
            # Azure Text (Fast but maybe inaccurate)
            azure_text = evt.text
            if not azure_text:
                return

            # Hybrid Mode: Capture Audio & Use Groq
            audio_snapshot = bytes(self.user_audio_buffer)
            self.user_audio_buffer = bytearray() # Reset buffer for next turn

            # Dispatch async work
            asyncio.run_coroutine_threadsafe(self._handle_recognized_async(azure_text, audio_snapshot), self.loop)

    async def _handle_recognized_async(self, text, audio_data=None):
        logging.info(f"Azure VAD Detected: {text}")

        # FILTER: Minimum Characters (Noise Reduction)
        min_chars = getattr(self.config, 'input_min_characters', 1)
        if len(text.strip()) < min_chars:
             logging.info(f"🔇 Ignoring short input ('{text}') < {min_chars} chars.")
             return

        # VALID INPUT - RESET IDLE TIMER HERE
        self.last_interaction_time = time.time()
        self.idle_retries = 0 # RESET RETRY COUNTER
        logging.warning(f"✅ [VALID INPUT] '{text}' passed filter ({len(text)} chars). Timer Reset.")

        # CRITICAL FIX: TRIGGER INTERRUPTION IF BOT IS SPEAKING
        # ALSO: Force clear client audio regardless of server state (Barge-in for buffered audio)
        if self.client_type == "browser":
             await self.websocket.send_text(json.dumps({"event": "clear"}))

        if self.is_bot_speaking:
            logging.warning("⚡ [INTERRUPTION] User spoke while bot was speaking. Stopping audio.")
            # We treat this as a server-side interruption event
            await self.handle_interruption(text)


        # SMART RESUME: Check for false alarms (noise)
        if self.client_type == "browser":
             threshold = getattr(self.config, 'interruption_threshold', 5)
        else:
             threshold = getattr(self.config, 'interruption_threshold_phone', 2)

        if self.was_interrupted and len(text) < threshold:
             logging.info(f"🛡️ Smart Resume Triggered! Interruption was likely noise ('{text}'). Resuming speech.")
             self.was_interrupted = False

             # Logic:
             # 1. We cancelled the previous task, so we MUST start a new one to continue speaking.
             # 2. We use 'intro_text' to say "Como le decía..." first.
             # 3. We insert a fake User prompt to tell the LLM to continue.

             resume_msg = "Como le decía..."
             self.conversation_history.append({"role": "user", "content": "(Hubo ruido de fondo, por favor continúa exactamente donde te quedaste)"})

             response_id = str(uuid.uuid4())[:8]
             self.response_task = asyncio.create_task(self.generate_response(response_id, intro_text=resume_msg))
             return

        self.was_interrupted = False # Reset if valid speech



        # QUALITY UPGRADE: Re-transcribe with Groq Whisper if audio available
        if audio_data and len(audio_data) > 0:
            logging.info("📝 Sending audio to Groq Whisper for better transcription...")
            try:
                # Wrap raw bytes in WAV container (Required by Groq/Whisper)
                # Assuming PCM 16kHz 16-bit for Browser (Simulator uses this default)
                # Logic can be refined for Twilio (8kHz MuLaw) later if needed
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2) # 16-bit
                    rate = 16000 if self.client_type == "browser" else 8000
                    wav_file.setframerate(rate)
                    wav_file.writeframes(audio_data)
                wav_data = wav_io.getvalue()

                lang_code = "es"
                if self.config and hasattr(self.config, "stt_language"):
                    lang_code = self.config.stt_language.split('-')[0]

                groq_text = await self.llm_provider.transcribe_audio(wav_data, language=lang_code)
                if groq_text and len(groq_text.strip()) > 0:
                    logging.info(f"🗣️ [IN] USER TEXT (Groq): {groq_text}")
                    text = groq_text
                else:
                    logging.warning("Groq transcription empty, falling back to Azure.")
            except Exception as e:
                logging.error(f"Groq Transcription Failed: {e}")

        # --- HALLUCINATION BLOCKLIST ---
        blacklist_str = getattr(self.config, 'hallucination_blacklist', "Pero.,Y...,Mm.")
        if self.client_type != 'browser':
             blacklist_str = getattr(self.config, 'hallucination_blacklist_phone', "Pero.,Y...,Mm.")

        blacklist = [w.strip() for w in blacklist_str.split(',') if w.strip()]
        clean_text = text.strip()
        # Case insensitive exact match (hallucinations are usually exact phrases)
        if any(clean_text.lower() == blocked.lower() for blocked in blacklist):
             logging.warning(f"🛡️ [BLOCKLIST] Ignored hallucination '{clean_text}' found in blacklist.")
             return

        # --- ADAPTIVE FILTERING ---
        # Get Min Chars from Config
        min_chars = getattr(self.config, 'input_min_characters', 4)
        if self.client_type != 'browser':
             min_chars = getattr(self.config, 'input_min_characters_phone', 2)

        should_filter, reason = self.vad_filter.should_filter(text, self.current_turn_max_rms, min_chars=min_chars)
        if should_filter:
             logging.warning(f"🛡️ [ADAPTIVE FILTER] Ignored input '{text}'. Reason: {reason}")
             return

        # Explicit Clarification Check?
        # If valid but low confidence (e.g. just barely passed or very short text), assume it's ambiguous?
        # For now, let's trust the 'should_filter' result.

        logging.info(f"FINAL USER TEXT: {text}")

        # ------------------------------------------------------------------
        # SMART INTERRUPTION LOGIC
        # If Bot is speaking, we must be strict about what counts as "New Input"
        # to avoid Echo triggering a new turn.
        # ------------------------------------------------------------------
        if self.is_bot_speaking:
            # Check Threshold
            if self.client_type == "browser":
                 threshold = getattr(self.config, 'interruption_threshold', 10)
            else:
                 threshold = getattr(self.config, 'interruption_threshold_phone', 5)
            # Tuning for Telnyx PSTN Noise
            if self.client_type == "telnyx":
                self.config.voice_sensitivity = getattr(self.config, 'voice_sensitivity_telnyx', 5000) # Increased default
                self.config.interruption_threshold = getattr(self.config, 'interruption_threshold_telnyx', 2)

            # STOP WORD BYPASS (If user says "Espera", "Para", etc. interrupt immediately)
            is_stop_command = any(word in text.lower() for word in ["espera", "para", "alto", "stop", "oye", "disculpa", "perdona"])

            if len(text) < threshold and not is_stop_command:
                 logging.info(f"🛡️ IGNORED ECHO/NOISE: '{text}' (Length {len(text)} < Threshold {threshold}) while Bot speaking.")
                 # Do NOT cancel current task. Do NOT start new task.
                 # Just treat this as noise.
                 return

            logging.warning(f"⚠️ OVERLAP DETECTED: User spoke ('{text}') while Bot was speaking. Cancelling current speech.")

        # Cancel any ongoing response generation (e.g. overlapping turns or fragmented speech)
        if self.response_task and not self.response_task.done():
            logging.info("🛑 Cancelling previous response task used to avoid double audio.")
            self.response_task.cancel()

        # Send transcript to UI immediately
        if self.client_type == "browser":
             await self.websocket.send_text(json.dumps({"type": "transcript", "role": "user", "text": text}))

        if self.stream_id:
            await db_service.log_transcript(self.stream_id, "user", text, call_db_id=self.call_db_id)

        self.conversation_history.append({"role": "user", "content": text})

        # Create new task
        response_id = str(uuid.uuid4())[:8]
        logging.info(f"🚀 Starting new response generation (ID: {response_id})")
        self.response_task = asyncio.create_task(self.generate_response(response_id))
        await self.response_task

    async def handle_interruption(self, text: str = ""):
        # Sensitivity Logic: Ignore short blips (Ambient Noise)
        if self.client_type == "browser":
             threshold = getattr(self.config, 'interruption_threshold', 5)
        else:
             threshold = getattr(self.config, 'interruption_threshold_phone', 2)

        # Let's use a dynamic logic: Only interrupt if > threshold
        if text and len(text) < threshold:
             return

        logging.info(f"⚡ Interruption Handler Triggered by: '{text}'")

        self.is_bot_speaking = False
        self.was_interrupted = True # Mark as interrupted

        if self.response_task and not self.response_task.done():
            logging.info("🛑 Cancelling response task due to interruption.")
            self.response_task.cancel()

            # Stop Frontend Audio Immediately
            if self.client_type == "browser":
                 await self.websocket.send_text(json.dumps({"event": "clear"}))

            if self.stream_id:
                  await self.stt_provider.stop_recognition() # Restart recognition cycle if needed?
                  # Actually Azure might need valid stop/start or continuous handles it.
                  pass

        # Send clear signal to both Twilio and Browser to stop audio
        should_send_clear = (self.client_type != "telnyx")

        if should_send_clear:
             msg = {"event": "clear"}
             if self.stream_id and self.client_type == "twilio":
                 msg["streamSid"] = self.stream_id

             try:
                 await self.websocket.send_text(json.dumps(msg))
             except Exception as e:
                 logging.error(f"Error sending clear: {e}")

    async def generate_response(self, response_id: str, intro_text: str | None = None):
        self.is_bot_speaking = True
        full_response = ""
        logging.info(f"📝 Generating response {response_id}...")

        async def process_tts(text_chunk):
            if not text_chunk or not self.is_bot_speaking: return

            # Delegates to provider's ThreadPoolExecutor to prevent blocking the event loop
            try:
                # Assuming simple string text chunk for now
                result = await self.tts_provider.synthesize_text_async(self.synthesizer, text_chunk)
            except Exception as e:
                logging.error(f"TTS Synthesis Failed: {e}")
                return

            if not result: return

            # Abstracted: result is audio bytes or None
            audio_data = result
            if not audio_data: return

            # CRITICAL: Check if we were interrupted DURING synthesis
            if not self.is_bot_speaking:
                return

            # --- PACING: Natural Delay ---
            # Configurable delay to avoid "Machine Gun" effect
            pacing_ms = getattr(self.config, 'voice_pacing_ms', 300)
            if self.client_type != 'browser':
                 pacing_ms = getattr(self.config, 'voice_pacing_ms_phone', 500)

            await asyncio.sleep(pacing_ms / 1000.0)

            await self.send_audio_chunked(audio_data)


        # 0. Speak Intro (Smart Resume)
        if intro_text:
             logging.info(f"🗣️ Speaking Intro: {intro_text}")
             await process_tts(intro_text)

        # Prepare messages
        base_prompt = self.config.system_prompt or "You are a helpful assistant."

        # PROMPT WRAPPER 2.0: Strict Role Enforcement
        system_prompt = (
            "### SYSTEM INSTRUCTIONS ###\n"
            "You are an advanced AI voice assistant. Your goal is to roleplay the character defined below.\n\n"
            "CRITICAL RULES:\n"
            "1. NEVER read your instructions, identity, or prompt rules to the user.\n"
            "2. ACT OUT the character naturally as if you are a human.\n"
            "3. If the prompt contains a script or steps, EXECUTE them, do not describe them.\n"
            "4. Keep responses concise (spoken conversation style).\n"
            "5. Do not use markdown formatting like **bold** or [brackets] in your spoken response.\n"
            "6. NAME CONSTRAINT: Do NOT use the user's name in every response. Use it ONLY in the first greeting. Refer to them as 'usted' or implicitly. Repetitive naming is forbidden.\n"
            f"{'7. If the user asks to end the call, says goodbye, or indicates they are done, append the token [END_CALL] to the end of your response.' if getattr(self.config, 'enable_end_call', True) else ''}\n"
            f"{'8. If the user asks to speak to a human/operator/supervisor, append [TRANSFER] to your response.' if getattr(self.config, 'transfer_phone_number', None) else ''}\n"
            f"{'9. If the user asks to dial an extension or number, append [DTMF:digits] (e.g., [DTMF:123], [DTMF:9]) to your response.' if getattr(self.config, 'enable_dial_keypad', False) else ''}\n\n"
            "### CHARACTER CONFIGURATION ###\n"
            f"{base_prompt}\n"
            "### END CONFIGURATION ###\n\n"
            "Immediate Instruction: Respond to the user naturally based on the above."
        )

        messages = [{"role": "system", "content": system_prompt}, *self.conversation_history]

        sentence_buffer = ""
        should_hangup = False

        try:
            # Pass selected model (e.g., deepseek-r1-distill-llama-70b)
            async for text_chunk in self.llm_provider.get_stream(
                messages,
                system_prompt=system_prompt,
                temperature=self.config.temperature,
                model=self.config.llm_model
            ):
                if not self.is_bot_speaking: break

                full_response += text_chunk
                sentence_buffer += text_chunk

                # ------------------------------------------------------------------
                # TOKEN DETECTION LOGIC (End Call, Transfer, DTMF)
                # ------------------------------------------------------------------

                # Check for [END_CALL]
                if "[END_CALL]" in sentence_buffer:
                    should_hangup = True
                    sentence_buffer = sentence_buffer.replace("[END_CALL]", "")

                # Check for [TRANSFER]
                if "[TRANSFER]" in sentence_buffer:
                     logging.warning("🔀 [TOKEN] Transfer Requested by AI")
                     # Execute Transfer Logic
                     target_phone = getattr(self.config, 'transfer_phone_number', None)
                     if target_phone:
                          # Run in background or await?
                          # Await might block TTS, but transfer usually ends call flow.
                          asyncio.create_task(self._perform_transfer(target_phone))
                          # Stop TTS? Only if we want immediate silence.
                     else:
                          logging.warning("⚠️ Transfer requested but no number configured.")

                     sentence_buffer = sentence_buffer.replace("[TRANSFER]", "")

                # Check for [DTMF:...]
                # Pattern: [DTMF:123], [DTMF:9], etc.
                if "[DTMF:" in sentence_buffer and "]" in sentence_buffer:
                     import re
                     # Find all occurrences
                     dtmf_matches = re.findall(r"\[DTMF:([0-9\*\#]+)\]", sentence_buffer)
                     for digits in dtmf_matches:
                          logging.warning(f"🎹 [TOKEN] DTMF Requested: {digits}")
                          asyncio.create_task(self._perform_dtmf(digits))

                     # Remove tokens from spoken text
                     sentence_buffer = re.sub(r"\[DTMF:[0-9\*\#]+\]", "", sentence_buffer)

                # ------------------------------------------------------------------

                # Logic: Flush on punctuation, but keep a small buffer (tail) if we suspect a split token?
                # Simpler: Just check split. If [END is at the end, don't flush yet?
                # To handle split e.g. "Bye [END", we should wait.

                # Check if buffer ends with partial token
                if sentence_buffer.endswith("[") or sentence_buffer.endswith("[END") or sentence_buffer.endswith("[TRAN") or sentence_buffer.endswith("[DT"):
                     continue # Wait for next chunk

                if any(punct in text_chunk for punct in [".", "?", "!", "\n"]):
                    # Safety clean again just in case tokens were re-added or split resolved
                    if "[END_CALL]" in sentence_buffer:
                         should_hangup = True
                         sentence_buffer = sentence_buffer.replace("[END_CALL]", "")

                    logging.info(f"🔊 [OUT] TTS SENTENCE: {sentence_buffer}")
                    await process_tts(sentence_buffer)
                    sentence_buffer = ""

            # Process remaining buffer
            if sentence_buffer and self.is_bot_speaking:
                # final cleanup
                if "[END_CALL]" in sentence_buffer: should_hangup = True
                sentence_buffer = sentence_buffer.replace("[END_CALL]", "")
                sentence_buffer = sentence_buffer.replace("[TRANSFER]", "")
                # Clean DTMF if any left
                import re
                sentence_buffer = re.sub(r"\[DTMF:[0-9\*\#]+\]", "", sentence_buffer)

                await process_tts(sentence_buffer)

            if self.stream_id and full_response:
                await db_service.log_transcript(self.stream_id, "assistant", full_response, call_db_id=self.call_db_id)

            self.conversation_history.append({"role": "assistant", "content": full_response})

        except asyncio.CancelledError:
            logging.info("Response generation cancelled.")
        except Exception as e:
            logging.error(f"Generate Response Critical Error: {e}", exc_info=True)
        finally:
            self.last_interaction_time = time.time()

            # CRITICAL FIX: Save partial response to history so context isn't lost
            if full_response and self.conversation_history[-1]["content"] != full_response:
                 pass # Already handled by specific check below

            # Update history if not already updated (Normal path updates at line 592/591)
            # Logic: If we are here, and full_response > 0, check if it's in history.
            is_already_saved = (len(self.conversation_history) > 0 and
                                self.conversation_history[-1]["role"] == "assistant" and
                                self.conversation_history[-1]["content"] == full_response)

            if not is_already_saved and full_response:
                 logging.info(f"💾 Saving partial response to history: {full_response[:50]}...")
                 self.conversation_history.append({"role": "assistant", "content": full_response})
                 if self.stream_id:
                     from app.db import AsyncSessionLocal
                     async with AsyncSessionLocal() as session:
                         await db_service.log_transcript(session, self.stream_id, "assistant", full_response + " [INTERRUPTED]", call_db_id=self.call_db_id)

            # For Browser, wait for speech_ended
            # For Twilio, we assume immediate completion (or handle differently)
            if self.client_type.lower() != "browser":
                self.is_bot_speaking = False
            else:
                 logging.info("🕒 [BROWSER] Waiting for speech_ended (Response Task Done).")

            if should_hangup:
                logging.info("📞 LLM requested hangup. Sending End-Control-Packet.")
                if self.stream_id:
                     from app.db import AsyncSessionLocal
                     async with AsyncSessionLocal() as session:
                         await db_service.log_transcript(session, self.stream_id, "system", "Call ended by AI ([END_CALL] token generated)", call_db_id=self.call_db_id)

                # Send JSON command to client to hangup AFTER audio is done
                if self.client_type == "browser":
                    await self.websocket.send_text(json.dumps({"type": "control", "action": "end_call"}))
                else:
                     # For Twilio, wait and close
                     await asyncio.sleep(5.0)
                     await self.websocket.close()

    async def process_audio(self, payload):
        try:
            # Reverted to standard decoding as requested

            # Simple padding fix
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += '=' * (4 - missing_padding)

            audio_bytes = base64.b64decode(payload)

            # ------------------------------------------------------------------
            # MANUAL DECODE: Convert Twilio/Telnyx Audio -> PCM (16-bit)
            # ------------------------------------------------------------------
            if self.client_type in ["twilio", "telnyx"]:
                  try:
                      # Telephony (Twilio/Telnyx) defaults to Mu-Law (PCMU)
                      # We decode Mu-Law -> Linear PCM for VAD and Azure PushStream
                      if hasattr(self, 'audio_encoding') and self.audio_encoding == 'PCMA':
                          audio_bytes = audioop.alaw2lin(audio_bytes, 2)
                      else:
                          # Default to PCMU (Mu-Law)
                          audio_bytes = audioop.ulaw2lin(audio_bytes, 2)

                  except Exception as e_conv:
                      logging.error(f"Audio Conversion Error (Legacy): {e_conv}")
                      return
            # ------------------------------------------------------------------

            # ------------------------------------------------------------------

            # Initialize chunk counter if missing
            if not hasattr(self, '_audio_chunk_count'):
                self._audio_chunk_count = 0
            self._audio_chunk_count += 1

            # DIAGNOSTICS: Calculate Volume Metrics
            try:
                # RMS (Average Volume) - Good for silence vs background vs voice
                rms = audioop.rms(audio_bytes, 2)
                # Max (Peak Volume) - Good for sudden spikes (clacks, pops)
                max_val = audioop.max(audio_bytes, 2)

                # Dynamic Thresholds (Trust the Overlay!)
                # "voice_sensitivity" is already updated by the overlay block in start()
                vad_threshold = getattr(self.config, 'voice_sensitivity', 500)

                classification = "🔇 Silence"

                # Check VAD
                if rms > vad_threshold:
                    classification = "🗣️ VOICE"
                elif rms > (vad_threshold / 2):
                    classification = "🔊 Noise"
                elif max_val > 25000:
                    classification = "💥 SPIKE"

                logging.warning(f"🎤 [AUDIO IN] RMS: {rms:<5} | Peak: {max_val:<5} | {classification} | Bytes: {len(audio_bytes)}")

                # ------------------------------------------------------------------
                # NOISE GATING (The "Gate")
                # ------------------------------------------------------------------
                enable_vad = getattr(self.config, 'enable_vad', True)
                if enable_vad and rms < vad_threshold:
                     # Silence/Noise detected. Send SILENCE to Azure STT to keep stream alive.
                     # This allows Azure's "Segmentation Silence" timer to advance.
                     silence_chunk = bytes(len(audio_bytes))
                     try:
                        self.recognizer.write(silence_chunk)
                     except Exception as e_push_silence:
                        logging.error(f"❌ [DEBUG] Failed to write silence to Azure STT: {e_push_silence}")

                     if self._audio_chunk_count % 50 == 1:
                         logging.warning(f"🔇 [VAD GATE] Sent SILENCE. RMS {rms} < Threshold {vad_threshold}")
                     return
                # ------------------------------------------------------------------

                # ------------------------------------------------------------------
                # LOCAL VAD (CALIBRATION): Reset Idle Timer on Voice Activity
                # ------------------------------------------------------------------
                # If we hear loud audio, we know the user is there.
                if rms > 1000:
                    self.last_interaction_time = time.time()
                # ------------------------------------------------------------------

            except Exception as e_metric:
                 logging.error(f"Error calculating metrics: {e_metric}")

            # DEBUG: Log before sending to Azure STT (reduced verbosity)
            # _audio_chunk_count is incremented at the start of metrics block

            # Only log every 50 chunks to reduce noise
            if self._audio_chunk_count % 50 == 1:
                logging.info(f"🔊 [AUDIO] Chunk #{self._audio_chunk_count}: Sending {len(audio_bytes)} bytes to Azure STT")

            try:
                self.recognizer.write(audio_bytes)
                if self._audio_chunk_count % 50 == 1:
                    logging.info(f"✅ [AUDIO] Successfully sent chunk #{self._audio_chunk_count}")
            except Exception as e_push:
                logging.error(f"❌ [DEBUG] Failed to write to Azure STT push_stream: {e_push}")

            self.user_audio_buffer.extend(audio_bytes)
        except Exception as e:
            # Detailed Logging for debugging
            preview = payload[:50] + "..." + payload[-50:] if payload and len(payload) > 100 else payload
            logging.error(f"Error processing audio: {e} | Payload Len: {len(payload) if payload else 0} | Preview: {preview}")

    # -------------------------------------------------------------------------
    # TELNYX FUNCTIONS (Audit Implementation)
    # -------------------------------------------------------------------------
    async def _perform_transfer(self, target_number: str):
        """
        Executes a call transfer via Telnyx API.
        Docs: https://developers.telnyx.com/docs/api/v2/call-control/Call-Commands#CallTransfer
        """
        if self.client_type != "telnyx" or not self.stream_id:
            logging.error("❌ Transfer failed: Not a Telnyx call or missing stream_id/call_control_id")
            return

        # Note: self.stream_id IS the call_control_id for Telnyx in this architecture
        call_control_id = self.stream_id
        url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/transfer"

        headers = {
            "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "to": target_number,
            # "webhook_url": ... (Optional, use existing app webhook)
        }

        try:
            logging.warning(f"📞 [TRANSFER] Initiating transfer to {target_number}...")
            from app.core.http_client import http_client
            client = http_client.get_client()
            resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code == 200:
                logging.warning("✅ [TRANSFER] Command accepted by Telnyx.")
                # We might want to stop speaking/listening here
                self.is_bot_speaking = False
            else:
                logging.error(f"❌ [TRANSFER] Failed: {resp.status_code} - {resp.text}")

        except Exception as e:
            logging.error(f"❌ [TRANSFER] Exception: {e}")

    async def _perform_dtmf(self, digits: str):
        """
        Sends DTMF tones via Telnyx API.
        Docs: https://developers.telnyx.com/docs/api/v2/call-control/Call-Commands#CallSendDTMF
        """
        if self.client_type != "telnyx" or not self.stream_id:
            logging.error("❌ DTMF failed: Not a Telnyx call")
            return

        call_control_id = self.stream_id
        url = f"{settings.TELNYX_API_BASE}/calls/{call_control_id}/actions/send_dtmf"

        headers = {
            "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "digits": digits
        }

        try:
            logging.warning(f"ww [DTMF] Sending digits: {digits}")
            from app.core.http_client import http_client
            client = http_client.get_client()
            resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code == 200:
                logging.info("✅ [DTMF] Sent successfully.")
            else:
                logging.error(f"❌ [DTMF] Failed: {resp.status_code} - {resp.text}")

        except Exception as e:
            logging.error(f"❌ [DTMF] Exception: {e}")
