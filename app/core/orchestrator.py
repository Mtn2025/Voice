import asyncio
import json
import base64
import logging
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
        self.call_db_id = None # Initialize to None
        self.config = None
        
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
        if len(evt.result.text) > 3 and self.is_bot_speaking:
            logging.info("Interruption detected! Stopping audio.")
            asyncio.create_task(self.handle_interruption())

    def handle_recognized(self, evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text = evt.result.text
            if not text: return
            # Dispatch async work to the main loop
            asyncio.run_coroutine_threadsafe(self._handle_recognized_async(text), self.loop)

    async def _handle_recognized_async(self, text):
        logging.info(f"USER SAID: {text}")
        
        # Cancel any ongoing response generation (e.g. overlapping turns or fragmented speech)
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
        
        # Send transcript to UI immediately
        if self.client_type == "browser":
             await self.websocket.send_text(json.dumps({"type": "transcript", "role": "user", "text": text}))

        if self.stream_id:
            await db_service.log_transcript(self.stream_id, "user", text, call_db_id=self.call_db_id)
        
        self.conversation_history.append({"role": "user", "content": text})
        
        # Create new task
        self.response_task = asyncio.create_task(self.generate_response())
        await self.response_task

    async def handle_interruption(self):
        self.is_bot_speaking = False
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
            
        # Send clear signal to both Twilio and Browser to stop audio
        msg = {"event": "clear", "streamSid": self.stream_id}
        await self.websocket.send_text(json.dumps(msg))

    async def generate_response(self):
        self.is_bot_speaking = True
        full_response = ""
        
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
                    b64_audio = base64.b64encode(audio_data).decode("utf-8")
                    msg = {
                        "event": "media",
                        "streamSid": self.stream_id,
                        "media": {"payload": b64_audio}
                    }
                    await self.websocket.send_text(json.dumps(msg))
                else:
                    # Browser expects raw bytes or base64? Let's send base64 with a specialized event
                    b64_audio = base64.b64encode(audio_data).decode("utf-8")
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
        except Exception as e:
            logging.error(f"Error processing audio: {e}")
