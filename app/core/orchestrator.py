import asyncio

# MODERNIZED AUDIO PIPELINE (NumPy)
from app.core.audio_processor import AudioProcessor

import base64
import contextlib
import json
import logging
import pathlib
import time
import uuid

from fastapi import WebSocket

from app.core.config import settings  # conftest.py sets env vars before import
from app.core.service_factory import ServiceFactory
from app.core.vad_filter import AdaptiveInputFilter  # VAD Filter module
from app.db.database import AsyncSessionLocal
from app.services.base import STTEvent, STTResultReason
from app.services.db_service import db_service

# AdaptiveInputFilter moved to app.core.vad_filter
# Import: from app.core.vad_filter import AdaptiveInputFilter


class VoiceOrchestrator:
    def __init__(self, websocket: WebSocket, client_type: str = "twilio") -> None:
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

        # --- Providers (Initialized in start) ---
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

    async def send_audio_chunked(self, audio_data: bytes) -> None:
        """
        PRODUCER: Queues audio chunks for the continuous stream loop.
        Breaks down large TTS buffers into 20ms chunks (160 bytes for telephony).
        """
        if self.client_type == "browser":
             # Browser still uses direct send (for now, or can be unified later)
             # Browser is robust enough for gaps, but unification is cleaner.
             # Keeping legacy path for browser to avoid regression there.
             b64 = base64.b64encode(audio_data).decode("utf-8")
             logging.info(f"📤 [BROWSER] Sending audio chunk: {len(audio_data)} bytes")
             await self.websocket.send_text(json.dumps({"type": "audio", "data": b64}))
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
            while True:
                if self.websocket.client_state == 3: # PREVENT CRASH ON CLOSED SOCKET
                    break

                # 1. TIMING: Target 20ms (0.02s)
                loop_start = asyncio.get_running_loop().time()

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
                elapsed = asyncio.get_running_loop().time() - loop_start
                if elapsed < 0.02:
                    await asyncio.sleep(0.02 - elapsed)

        except asyncio.CancelledError:
             logging.error("🌊 [STREAM] Loop Cancelled")
        except Exception as e_loop:
             logging.error(f"🌊 [STREAM] Loop Crash: {e_loop}")

    async def _synthesize_text(self, text: str) -> bytes | None:
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

    def update_vad_stats(self, rms: float) -> None:
        """Called by routes.py when client sends VAD stats."""
        # Update self-calibration profile
        self.vad_filter.update_profile(rms)
        self.current_turn_max_rms = rms
        logging.info(f"📊 [VAD STATS] RMS: {rms:.4f} | Avg: {self.vad_filter.avg_rms:.4f} | Samples: {self.vad_filter.samples}")

    async def speak_direct(self, text: str) -> None:
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
                audio_data = await self._synthesize_text(text)
                if audio_data:
                     await self.send_audio_chunked(audio_data)

            # Log
            self.conversation_history.append({"role": "assistant", "content": text})
            if self.stream_id:
               logging.info(f"💾 [LOG-DB] ASSISTANT: {text}")
               async with AsyncSessionLocal() as session:
                   await db_service.log_transcript(session, self.stream_id, "assistant", text + " [IDLE]", call_db_id=self.call_db_id)

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

    async def monitor_idle(self) -> None:
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
                logging.warning(f"🔍 [IDLE-CHECK] Speaking: {self.is_bot_speaking} | Elapsed: {now - self.last_interaction_time:.2f}s | StartDelta: {now - self.start_time:.2f}")

                if not self.is_bot_speaking and (now - self.last_interaction_time > idle_timeout) and await self._handle_idle_timeout_logic(now):
                    break

            except Exception as e:
                 logging.warning(f"Monitor error: {e}")

    async def _handle_idle_timeout_logic(self, now: float) -> bool:
        """Handles idle timeout logic, including retries and hangup. Returns True if loop should break."""
        if not hasattr(self, 'idle_retries'):
             self.idle_retries = 0

        max_retries = getattr(self.config, 'inactivity_max_retries', 3)
        logging.warning(f"zzz Idle timeout reached. Retry {self.idle_retries + 1}/{max_retries}")

        if self.idle_retries >= max_retries:
             logging.warning("🛑 Max idle retries reached. Ending call.")
             if self.client_type == "browser":
                 await self.websocket.close()
             elif self.client_type == "telnyx":
                  pass # Should trigger end call hook if implemented

             if self.stream_id:
                 async with AsyncSessionLocal() as session:
                     await db_service.log_transcript(session, self.stream_id, "system", f"Call ended by System (Max Idle Retries: {max_retries})", call_db_id=self.call_db_id)

             await self.websocket.close()
             return True

        self.idle_retries += 1
        msg = getattr(self.config, 'idle_message', "¿Hola? ¿Sigue ahí?")
        if msg:
           self.last_interaction_time = now # Reset to wait again
           self._create_background_task(self.speak_direct(msg))
        return False


    async def start(self) -> None:
        # ... (no change to start) ...



        # Capture the current event loop to schedule tasks from sync callbacks
        self.loop = asyncio.get_running_loop()

        # Load Config
        await self._load_config_from_db()

        logging.warning("🎯 [TRACE] Config loaded, starting profile overlay...")
        self._apply_profile_overlay()

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
        self._initialize_providers()

        # Setup STT (Azure)
        self._setup_stt()

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
        self._handle_first_message()

    async def stop(self) -> None:
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
                logging.info("🔌 Running Post-Call Analysis...")
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
        self.idle_retries = 0  # CRITICAL FIX: Reset retries on valid activity

    # REMOVED: handle_canceled, handle_session_stopped (handled by generic event logic)

    def handle_recognition_event(self, evt: STTEvent) -> None:
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

    async def _handle_recognized_async(self, text: str, audio_data: bytes | None = None) -> None:
        logging.info(f"Azure VAD Detected: {text}")

        # UI OBSERVABILITY: Send transcript immediately (Browser only)
        if self.client_type == "browser":
             try:
                 await self.websocket.send_text(json.dumps({"type": "transcript", "role": "user", "text": text}))
             except Exception:
                 pass

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
        if self._handle_smart_resume(text):
            return

        self.was_interrupted = False # Reset if valid speech



        # QUALITY UPGRADE: Re-transcribe with Groq Whisper if audio available
        groq_text = await self._transcribe_with_groq_if_needed(audio_data)
        if groq_text:
            text = groq_text

        # --- HALLUCINATION BLOCKLIST ---
        # --- HALLUCINATION BLOCKLIST ---
        if self._is_hallucination(text):
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
        # SMART INTERRUPTION LOGIC
        if self._check_interruption_policy(text):
             return

        # Cancel any ongoing response generation (e.g. overlapping turns or fragmented speech)
        if self.response_task and not self.response_task.done():
            logging.info("🛑 Cancelling previous response task used to avoid double audio.")
            self.response_task.cancel()

        # Send transcript to UI immediately - MOVED TO TOP
        # if self.client_type == "browser":
        #      await self.websocket.send_text(json.dumps({"type": "transcript", "role": "user", "text": text}))

        if self.stream_id:
            async with AsyncSessionLocal() as session:
                await db_service.log_transcript(session, self.stream_id, "user", text, call_db_id=self.call_db_id)

        self.conversation_history.append({"role": "user", "content": text})

        # Create new task
        response_id = str(uuid.uuid4())[:8]
        logging.info(f"🚀 Starting new response generation (ID: {response_id})")
        self.response_task = asyncio.create_task(self.generate_response(response_id))
        await self.response_task

    async def handle_interruption(self, text: str = "") -> None:
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

    async def _process_tts_chunk(self, audio_data: bytes) -> None:
        if not audio_data:
            return

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

    def _build_system_prompt(self) -> str:
        """Builds the system prompt with dynamic context (Date/Time)."""
        base_prompt = getattr(self.config, 'system_prompt', "Eres un asistente útil.")
        
        # Add Time Context
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        context_prompt = f"{base_prompt}\n\n[CONTEXT]\nCurrent Date/Time: {now}\n"
        
        return context_prompt

    async def _handle_stream_token(self, text_chunk: str, sentence_buffer: str, should_hangup: bool) -> tuple[str, bool]:
        """
        Processes a single token from LLM stream:
        1. Updates buffer
        2. Checks for control tokens ([END_CALL], [TRANSFER], [DTMF])
        3. Checks for sentence boundaries and triggers TTS
        """
        sentence_buffer += text_chunk

        # 1. Check for [TRANSFER]
        if "[TRANSFER]" in sentence_buffer:
             target_phone = getattr(self.config, 'transfer_phone_number', None)
             if target_phone:
                  logging.info(f"🔄 Transfer detected to {target_phone}")
                  self._create_background_task(self._perform_transfer(target_phone))
             else:
                  logging.warning("⚠️ Transfer requested but no number configured.")
             sentence_buffer = sentence_buffer.replace("[TRANSFER]", "")

        # 2. Check for [DTMF:...]
        if "[DTMF:" in sentence_buffer and "]" in sentence_buffer:
             import re
             dtmf_matches = re.findall(r"\[DTMF:([0-9\*\#]+)\]", sentence_buffer)
             for digits in dtmf_matches:
                  logging.info(f"🔢 DTMF detected: {digits}")
                  self._create_background_task(self._perform_dtmf(digits))
                  sentence_buffer = sentence_buffer.replace(f"[DTMF:{digits}]", "")

        # 3. Check for [END_CALL] (Preliminary check)
        if "[END_CALL]" in sentence_buffer and "[TOOL CALL]" in sentence_buffer:
             sentence_buffer = sentence_buffer.replace("[TOOL CALL]", "")

        # 4. Filter <think> tags (model's internal reasoning - should NOT be spoken)
        import re
        if "<think>" in sentence_buffer or "</think>" in sentence_buffer:
            # Remove everything between <think> and </think> including tags
            sentence_buffer = re.sub(r'<think>.*?</think>', '', sentence_buffer, flags=re.DOTALL)
            # Also handle unclosed think tags
            sentence_buffer = sentence_buffer.replace("<think>", "").replace("</think>", "")
            sentence_buffer = sentence_buffer.strip()
            # If buffer is now empty, skip TTS
            if not sentence_buffer:
                return should_hangup

        # 5. Sentence Boundary Check
        if any(punct in text_chunk for punct in [".", "?", "!", "\n"]):
            # Final check for End Call before speaking
            if "[END_CALL]" in sentence_buffer:
                should_hangup = True
                sentence_buffer = sentence_buffer.replace("[END_CALL]", "")
            if "[HANGUP]" in sentence_buffer:
                should_hangup = True
                sentence_buffer = sentence_buffer.replace("[HANGUP]", "")

            if sentence_buffer.strip():
                logging.info(f"🔊 [OUT] TTS SENTENCE: {sentence_buffer}")
                # FIX: Synthesize text -> Audio Bytes first!
                audio_bytes = await self._synthesize_text(sentence_buffer)
                if audio_bytes:
                    await self._process_tts_chunk(audio_bytes)
            sentence_buffer = ""

        return sentence_buffer, should_hangup

    async def _finalize_response(self, sentence_buffer: str, full_response: str, should_hangup: bool) -> None:
        """Handles post-response cleanup, history updates, and hangup logic."""
        # 1. Process Remaining Buffer
        if sentence_buffer and self.is_bot_speaking:
            if "[END_CALL]" in sentence_buffer:
                should_hangup = True
            sentence_buffer = sentence_buffer.replace("[END_CALL]", "")
            sentence_buffer = sentence_buffer.replace("[TRANSFER]", "")
            import re
            sentence_buffer = re.sub(r"\[DTMF:[0-9\*\#]+\]", "", sentence_buffer)
            # Filter think tags from final buffer too
            sentence_buffer = re.sub(r'<think>.*?</think>', '', sentence_buffer, flags=re.DOTALL)
            sentence_buffer = sentence_buffer.replace("<think>", "").replace("</think>", "")
            sentence_buffer = sentence_buffer.strip()
            if sentence_buffer:  # Only process if not empty after filtering
                await self._process_tts_chunk(sentence_buffer)

        # 2. Log Full Transcript (Success Path)
        if self.stream_id and full_response:
            async with AsyncSessionLocal() as session:
                await db_service.log_transcript(session, self.stream_id, "assistant", full_response, call_db_id=self.call_db_id)

            # UI OBSERVABILITY: Send Assistant Transcript (Browser only)
            logging.warning(f"🔍 [TRANSCRIPT DEBUG] client_type='{self.client_type}', sending={'YES' if self.client_type == 'browser' else 'NO'}")
            if self.client_type == "browser":
                try:
                    await self.websocket.send_text(json.dumps({"type": "transcript", "role": "assistant", "text": full_response}))
                    logging.warning(f"✅ [TRANSCRIPT] Sent assistant message to UI: {full_response[:50]}...")
                except Exception as e:
                    logging.error(f"❌ [TRANSCRIPT] Failed to send: {e}")
                    pass

        # 3. Update Conversation History (Common Path)
        # Note: If exception occurred, finally block will double check partials.
        # But here we are in success path.
        self.conversation_history.append({"role": "assistant", "content": full_response})

        # 4. Handle State & Hangup
        # For Browser, wait for speech_ended
        # For Twilio, we assume immediate completion (or handle differently)
        if self.client_type.lower() != "browser":
            self.is_bot_speaking = False
        else:
             logging.info("🕒 [BROWSER] Waiting for speech_ended (Response Task Done).")

        if should_hangup:
            logging.info("📞 LLM requested hangup. Sending End-Control-Packet.")
            if self.stream_id:
                 async with AsyncSessionLocal() as session:
                     await db_service.log_transcript(session, self.stream_id, "system", "Call ended by AI ([END_CALL] token generated)", call_db_id=self.call_db_id)

            if self.client_type == "browser":
                await self.websocket.send_text(json.dumps({"type": "control", "action": "end_call"}))
            else:
                 await asyncio.sleep(1.0)
                 await self.websocket.close()

    def _apply_profile_overlay(self) -> None: # noqa: PLR0912, PLR0915
        """Applies Telnyx/Phone specific overrides to the configuration."""
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

                  # --- Functions (Transfer / Keypad) ---
                  if conf.transfer_phone_number:
                      conf.transfer_phone_number = conf.transfer_phone_number

                  # Flow Control Overrides
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

        if self.client_type != "browser":
             logging.info(f"📱 [PROFILE APPLIED] Client: {self.client_type} | Voice: {self.config.voice_name} | STT: {self.config.stt_provider}")

    def _load_background_audio(self) -> None:
        """Loads background audio (WAV/Raw) if configured."""
        bg_sound = getattr(self.config, 'background_sound', 'none')
        if bg_sound and bg_sound.lower() != 'none' and self.client_type != 'browser':
             try:
                 sound_path = pathlib.Path(f"app/static/sounds/{bg_sound}.wav")

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

    async def generate_response(self, response_id: str, intro_text: str | None = None):
        self.is_bot_speaking = True
        full_response = ""
        logging.info(f"📝 Generating response {response_id}...")




        # 0. Speak Intro (Smart Resume)
        if intro_text:
             logging.info(f"🗣️ Speaking Intro: {intro_text}")
             await self._process_tts_chunk(intro_text)

        # Prepare messages
        # Prepare messages
        system_prompt = self._build_system_prompt()

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
                if not self.is_bot_speaking:
                    break

                full_response += text_chunk
                # Process Token
                sentence_buffer, should_hangup = await self._handle_stream_token(
                    text_chunk, sentence_buffer, should_hangup
                )

            # Process remaining buffer
            await self._finalize_response(sentence_buffer, full_response, should_hangup)

        except asyncio.CancelledError:
            logging.info("Response generation cancelled.")
        except Exception as e:
            logging.error(f"Generate Response Critical Error: {e}", exc_info=True)
        finally:
            self.last_interaction_time = time.time()

    async def process_audio(self, payload: str) -> None:
        try:
             audio_bytes = self._decode_audio_payload(payload)
             if not audio_bytes:
                 return

             # Initialize chunk counter if missing
             if not hasattr(self, '_audio_chunk_count'):
                self._audio_chunk_count = 0
             self._audio_chunk_count += 1

             self._handle_vad_and_push(audio_bytes)

             self.user_audio_buffer.extend(audio_bytes)
        except Exception as e:
             # Detailed Logging for debugging
             preview = payload[:50] + "..." + payload[-50:] if payload and len(payload) > 100 else payload
             logging.error(f"Error processing audio: {e} | Payload Len: {len(payload) if payload else 0} | Preview: {preview}")


    # -------------------------------------------------------------------------
    # TELNYX FUNCTIONS (Audit Implementation)
    # -------------------------------------------------------------------------
    async def _perform_transfer(self, target_number: str) -> None:
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

    async def _perform_dtmf(self, digits: str) -> None:
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

    def _handle_smart_resume(self, text: str) -> bool:
        """Checks if interruption was noise and resumes speech if so. Returns True if handled."""
        if self.client_type == "browser":
             threshold = getattr(self.config, 'interruption_threshold', 5)
        else:
             threshold = getattr(self.config, 'interruption_threshold_phone', 2)

        if self.was_interrupted and len(text) < threshold:
             logging.info(f"🛡️ Smart Resume Triggered! Interruption was likely noise ('{text}'). Resuming speech.")
             self.was_interrupted = False

             resume_msg = "Como le decía..."
             self.conversation_history.append({"role": "user", "content": "(Hubo ruido de fondo, por favor continúa exactamente donde te quedaste)"})

             response_id = str(uuid.uuid4())[:8]
             self.response_task = asyncio.create_task(self.generate_response(response_id, intro_text=resume_msg))
             return True
        self.was_interrupted = False # Reset if valid speech
        return False

    async def _transcribe_with_groq_if_needed(self, audio_data: bytes | None) -> str | None:
        """Refines transcription using Groq if audio data is available."""
        if not audio_data or len(audio_data) == 0:
            return None

        logging.info("📝 Sending audio to Groq Whisper for better transcription...")
        try:
            import io
            import wave
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
                return groq_text

            logging.warning("Groq transcription empty, falling back to Azure.")
        except Exception as e:
            logging.error(f"Groq Transcription Failed: {e}")
        return None

    def _is_hallucination(self, text: str) -> bool:
        """Checks if text matches hallucination blocklist."""
        blacklist_str = getattr(self.config, 'hallucination_blacklist', "Pero.,Y...,Mm.")
        if self.client_type != 'browser':
             blacklist_str = getattr(self.config, 'hallucination_blacklist_phone', "Pero.,Y...,Mm.")

        blacklist = [w.strip() for w in blacklist_str.split(',') if w.strip()]
        clean_text = text.strip()
        if any(clean_text.lower() == blocked.lower() for blocked in blacklist):
             logging.warning(f"🛡️ [BLOCKLIST] Ignored hallucination '{clean_text}' found in blacklist.")
             return True
        return False

    async def _load_config_from_db(self) -> None:
        """Loads configuration from database."""
        try:
            logging.warning("⚙️ [CONFIG] Attempting to load agent config from DB...")
            # Local import to avoid circular dependency/scope issues if any
            from app.db.database import AsyncSessionLocal
            from app.services.db_service import db_service

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

    def _decode_audio_payload(self, payload: str) -> bytes | None:
        """Decodes Base64 payload and converts to Linear PCM if needed."""
        # Simple padding fix
        missing_padding = len(payload) % 4
        if missing_padding:
            payload += '=' * (4 - missing_padding)

        audio_bytes = base64.b64decode(payload)

        # MANUAL DECODE: Convert Twilio/Telnyx Audio -> PCM (16-bit)
        if self.client_type in ["twilio", "telnyx"]:
              try:
                  if hasattr(self, 'audio_encoding') and self.audio_encoding == 'PCMA':
                      audio_bytes = AudioProcessor.alaw2lin(audio_bytes, 2)
                  else:
                      # Default to PCMU (Mu-Law)
                      audio_bytes = AudioProcessor.ulaw2lin(audio_bytes, 2)

              except Exception as e_conv:
                  logging.error(f"Audio Conversion Error (Legacy): {e_conv}")
                  return None
        return audio_bytes

    def _handle_vad_and_push(self, audio_bytes: bytes) -> None:
        """Calculates VAD metrics, applies Noise Gating, and pushes to recognizer."""
        try:
            # RMS (Average Volume)
            rms = AudioProcessor.rms(audio_bytes, 2)
            # Max (Peak Volume)
            max_val = AudioProcessor.max_val(audio_bytes, 2)

            # Dynamic Thresholds (Trust the Overlay!)
            vad_threshold = getattr(self.config, 'voice_sensitivity', 500)

            classification = "🔇 Silence"

            # Check VAD
            if rms > vad_threshold:
                classification = "🗣️ VOICE"
            elif rms > (vad_threshold / 2):
                classification = "🔊 Noise"
            elif max_val > 25000:
                classification = "💥 SPIKE"

            if self._audio_chunk_count % 50 == 1:
                logging.warning(f"🎤 [AUDIO IN] RMS: {rms:<5} | Peak: {max_val:<5} | {classification} | Bytes: {len(audio_bytes)}")


            # NOISE GATING
            enable_vad = getattr(self.config, 'enable_vad', True)
            if enable_vad and rms < vad_threshold:
                 # Silence/Noise detected. Send SILENCE to Azure STT.
                 silence_chunk = bytes(len(audio_bytes))
                 try:
                    self.recognizer.write(silence_chunk)
                 except Exception as e_push_silence:
                    logging.error(f"❌ [DEBUG] Failed to write silence to Azure STT: {e_push_silence}")

                 if self._audio_chunk_count % 50 == 1:
                     logging.warning(f"🔇 [VAD GATE] Sent SILENCE. RMS {rms} < Threshold {vad_threshold}")
                 return

            # LOCAL VAD (CALIBRATION): Reset Idle Timer on Voice Activity
            if rms > 1000:
                self.last_interaction_time = time.time()

        except Exception as e_metric:
             logging.error(f"Error calculating metrics: {e_metric}")

        # Push to Azure STT
        if self._audio_chunk_count % 50 == 1:
            logging.info(f"🔊 [AUDIO] Chunk #{self._audio_chunk_count}: Sending {len(audio_bytes)} bytes to Azure STT")

        try:
            self.recognizer.write(audio_bytes)
            if self._audio_chunk_count % 50 == 1:
                logging.info(f"✅ [AUDIO] Successfully sent chunk #{self._audio_chunk_count}")
        except Exception as e_push:
            logging.error(f"❌ [DEBUG] Failed to write to Azure STT push_stream: {e_push}")

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
                bg_lin = AudioProcessor.alaw2lin(bg_chunk, 2)

                if self.client_type == 'telnyx':
                    tts_lin = AudioProcessor.alaw2lin(tts_chunk, 2)
                else:
                    tts_lin = AudioProcessor.ulaw2lin(tts_chunk, 2)

                bg_lin_quiet = AudioProcessor.mul(bg_lin, 2, 0.15)
                mixed_lin = AudioProcessor.add(tts_lin, bg_lin_quiet, 2)

                if self.client_type == 'telnyx':
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

    def _check_interruption_policy(self, text: str) -> bool:
        """Determines if the input should interrupt the bot. Returns True if input should be ignored (noise)."""
        if not self.is_bot_speaking:
            return False

        # Check Threshold
        if self.client_type == "browser":
             threshold = getattr(self.config, 'interruption_threshold', 10)
        else:
             threshold = getattr(self.config, 'interruption_threshold_phone', 5)

        # Tuning for Telnyx PSTN Noise
        if self.client_type == "telnyx":
            self.config.voice_sensitivity = getattr(self.config, 'voice_sensitivity_telnyx', 5000)
            self.config.interruption_threshold = getattr(self.config, 'interruption_threshold_telnyx', 2)

        # STOP WORD BYPASS
        is_stop_command = any(word in text.lower() for word in ["espera", "para", "alto", "stop", "oye", "disculpa", "perdona"])

        if len(text) < threshold and not is_stop_command:
             logging.info(f"🛡️ IGNORED ECHO/NOISE: '{text}' (Length {len(text)} < Threshold {threshold}) while Bot speaking.")
             return True # Ignore

        logging.warning(f"⚠️ OVERLAP DETECTED: User spoke ('{text}') while Bot was speaking. Cancelling current speech.")
        return False

    def _handle_first_message(self) -> None:
        """Handles the logic for the initial greeting message."""
        first_mode = getattr(self.config, 'first_message_mode', 'speak-first')
        first_msg = getattr(self.config, 'first_message', "Hola, soy Andrea. ¿En qué puedo ayudarte?")
        logging.warning(f"🎤 [FIRST_MSG] Mode='{first_mode}', Msg='{first_msg}', Check={first_mode == 'speak-first' and bool(first_msg)}")

        if first_mode == 'speak-first' and first_msg:
             logging.warning("🎤 [FIRST_MSG] ✅ CREATING delayed_greeting task...")
             self.greeting_task = asyncio.create_task(self._delayed_greeting_task(first_msg))
             logging.warning(f"🎤 [FIRST_MSG] ✅ Task created: {self.greeting_task}")
        elif first_mode == 'speak-first-dynamic':
             # Placeholder
             pass

    async def _delayed_greeting_task(self, message: str) -> None:
        """Background task to wait for stream ready and speak greeting."""
        try:
            logging.warning("🔔 [GREETING] Function started")
            logging.warning(f"🔔 [GREETING] Message to speak: {message}")
            if self.client_type != "browser":
                logging.info("⏳ Waiting for Media Stream START event before greeting...")
                for _ in range(50): # Wait up to 5 seconds for Twilio/Telnyx
                    if self.stream_id:
                        logging.info(f"✅ StreamID obtained ({self.stream_id}). Speaking now.")
                        break
                    await asyncio.sleep(0.1)
                else:
                    logging.warning("⚠️ Timed out waiting for StreamID. Speaking anyway (might fail).")
            else:
                # Browser: Give a tiny pause to ensure WebSocket is fully ready to receive audio
                await asyncio.sleep(0.5)

            logging.info(f"🗣️ Triggering First Message: {message}")
            await self.speak_direct(message)
        except Exception as e:
            logging.error(f"❌ Error in delayed_greeting: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")

    def _initialize_providers(self) -> None:
        """Initializes LLM, STT, and TTS providers from factory."""
        logging.warning("🔧 [TRACE] About to initialize providers (STT/LLM/TTS)...")
        self.llm_provider = ServiceFactory.get_llm_provider(self.config)
        self.stt_provider = ServiceFactory.get_stt_provider(self.config)
        self.tts_provider = ServiceFactory.get_tts_provider(self.config)
        logging.warning("✅ [TRACE] Providers initialized successfully")

    def _setup_stt(self) -> None:
        """Configures and initializes STT recognizer."""
        silence_timeout = getattr(self.config, 'silence_timeout_ms', 500)
        if self.client_type != "browser":
             silence_timeout = getattr(self.config, 'silence_timeout_ms_phone', 2000)

        logging.warning(f"⚙️ [CONFIG] STT Silence Timeout: {silence_timeout}ms")

        # Load background audio first
        self._load_background_audio()

        self.recognizer = self.stt_provider.create_recognizer(
            language=getattr(self.config, 'stt_language', 'es-MX'),
            audio_mode=self.client_type,
            on_interruption_callback=self.handle_interruption,
            event_loop=self.loop,
            initial_silence_ms=getattr(self.config, 'initial_silence_timeout_ms', 30000),
            segmentation_silence_ms=silence_timeout
        )

        self.recognizer.subscribe(self.handle_recognition_event)
