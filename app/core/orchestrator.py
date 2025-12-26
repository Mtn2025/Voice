import asyncio
import json
import base64
import logging
import uuid
import azure.cognitiveservices.speech as speechsdk
from fastapi import WebSocket
from app.services.db_service import db_service
from app.core.service_factory import ServiceFactory

class VoiceOrchestrator:
    def __init__(self, websocket: WebSocket, client_type: str = "twilio"):
        """
        client_type: 'twilio' or 'browser'
        """
        self.websocket = websocket
        self.client_type = client_type
        self.conversation_history = []
        self.is_bot_speaking = False
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

    async def start(self):
        # ... (no change to start) ...
        # Capture the current event loop to schedule tasks from sync callbacks
        self.loop = asyncio.get_running_loop()

        # Load Config
        self.config = await db_service.get_agent_config()
        self.conversation_history.append({"role": "system", "content": self.config.system_prompt})
        
        # Instantiate Providers
        self.stt_provider = ServiceFactory.get_stt_provider(self.config)
        self.llm_provider = ServiceFactory.get_llm_provider(self.config)
        self.tts_provider = ServiceFactory.get_tts_provider(self.config)
        
        # Setup STT (Azure)
        # Note: In a pure abstract world, we'd wrap these events too, 
        # but for now we know it's Azure underlying.
        self.recognizer, self.push_stream = self.stt_provider.create_recognizer(language="es-MX", audio_mode=self.client_type)
        
        # Wire up Azure events
        self.recognizer.recognizing.connect(self.handle_recognizing)
        self.recognizer.recognized.connect(self.handle_recognized)
        
        # Setup TTS
        self.synthesizer = self.tts_provider.create_synthesizer(voice_name=self.config.voice_name, audio_mode=self.client_type)

        if self.stream_id:
            self.call_db_id = await db_service.create_call(self.stream_id)
            
        self.recognizer.start_continuous_recognition()

    async def stop(self):
        if self.response_task:
            self.response_task.cancel()
        if self.recognizer:
            self.recognizer.stop_continuous_recognition()

    def handle_recognizing(self, evt):
        if len(evt.result.text) > 0 and self.is_bot_speaking:
            logging.info(f"Interruption detected (Text: '{evt.result.text}')! Stopping audio.")
            asyncio.create_task(self.handle_interruption())

    def handle_recognized(self, evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            # Azure Text (Fast but maybe inaccurate)
            azure_text = evt.result.text
            if not azure_text: return
            
            # Hybrid Mode: Capture Audio & Use Groq
            audio_snapshot = bytes(self.user_audio_buffer)
            self.user_audio_buffer = bytearray() # Reset buffer for next turn
            
            # Dispatch async work
            asyncio.run_coroutine_threadsafe(self._handle_recognized_async(azure_text, audio_snapshot), self.loop)

    async def _handle_recognized_async(self, text, audio_data=None):
        logging.info(f"Azure VAD Detected: {text}")
        
        # QUALITY UPGRADE: Re-transcribe with Groq Whisper if audio available
        if audio_data and len(audio_data) > 0:
            logging.info("📝 Sending audio to Groq Whisper for better transcription...")
            try:
                groq_text = await self.llm_provider.transcribe_audio(audio_data)
                if groq_text and len(groq_text.strip()) > 0:
                    logging.info(f"✅ Groq Whisper Result: {groq_text}")
                    text = groq_text
                else:
                    logging.warning("Groq transcription empty, falling back to Azure.")
            except Exception as e:
                logging.error(f"Groq Transcription Failed: {e}")

        logging.info(f"FINAL USER TEXT: {text}")        

        # Overlap Detection Logic
        if self.is_bot_speaking:
            logging.warning(f"⚠️ OVERLAP DETECTED: User spoke while Bot was speaking. Current task will be cancelled.")
        
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

    async def handle_interruption(self):
        logging.info("⚡ Interruption Handler Triggered")
        self.is_bot_speaking = False
        if self.response_task and not self.response_task.done():
            logging.info("🛑 Cancelling response task due to interruption.")
            self.response_task.cancel()
            
        # Send clear signal to both Twilio and Browser to stop audio
        msg = {"event": "clear", "streamSid": self.stream_id}
        await self.websocket.send_text(json.dumps(msg))

    async def generate_response(self, response_id: str):
        self.is_bot_speaking = True
        full_response = ""
        logging.info(f"📝 Generating response {response_id}...")
        
        async def process_tts(text_chunk):
            if not text_chunk or not self.is_bot_speaking: return
            
            # Using Azure SSML to control speed could be added here
            # For now, raw text
            
            # Note: We are using the Azure SDK directly here via the provider
            # Ideally this logic is inside the provider's synthesize_stream
            # Wrapper for non-blocking execution of blocking Azure SDK call
            def synthesize_blocking():
                return self.synthesizer.speak_text_async(text_chunk).get()

            # Run in thread pool to avoid blocking asyncio loop
            try:
                result = await asyncio.to_thread(synthesize_blocking)
            except asyncio.CancelledError:
                return

            # CRITICAL: Check if we were interrupted DURING synthesis
            if not self.is_bot_speaking: 
                return
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                if self.client_type == "twilio":
                    # ... twilio logic ...
                    pass
                else:
                    # Browser expects raw bytes or base64? Let's send base64 with a specialized event
                    b64_audio = base64.b64encode(audio_data).decode("utf-8")
                    data_hash = hash(b64_audio)
                    logging.info(f"🔊 SENDING AUDIO PACKET | Hash: {data_hash} | Size: {len(b64_audio)}")
                    msg = {"type": "audio", "data": b64_audio}
                    await self.websocket.send_text(json.dumps(msg))

        buffer = ""
        try:
            async for token in self.llm_provider.get_stream(self.conversation_history, self.config.system_prompt, self.config.temperature):
                if not self.is_bot_speaking: break
                full_response += token
                buffer += token
                
                if any(p in buffer for p in [".", "?", "!", "\n"]):
                    await process_tts(buffer)
                    buffer = ""
            
            if buffer and self.is_bot_speaking:
                await process_tts(buffer)
                
            if self.stream_id and full_response:
                await db_service.log_transcript(self.stream_id, "assistant", full_response, call_db_id=self.call_db_id)
                
            self.conversation_history.append({"role": "assistant", "content": full_response})
            
        except asyncio.CancelledError:
            logging.info("Response generation cancelled.")
        finally:
            self.is_bot_speaking = False

    async def process_audio(self, payload):
        try:
            # Twilio sends base64. Browser (if sending binary) might need diff handling
            # Assuming Browser also sends base64 for consistency via WS
            audio_bytes = base64.b64decode(payload)
            self.push_stream.write(audio_bytes)
            self.user_audio_buffer.extend(audio_bytes)
        except Exception as e:
            logging.error(f"Error processing audio: {e}")
