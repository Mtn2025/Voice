import asyncio
from typing import Any, Optional, AsyncGenerator
from app.services.base import STTProvider, TTSProvider, LLMProvider, STTEvent, STTResultReason

# --- MOCK STT ---

class MockRecognizer:
    def __init__(self):
        self._callback = None
        self.is_running = False

    def subscribe(self, callback):
        self._callback = callback

    def start_continuous_recognition_async(self):
        class Future:
            def get(self): return None
        self.is_running = True
        return Future()

    def stop_continuous_recognition_async(self):
        class Future:
            def get(self): return None
        self.is_running = False
        return Future()

    # Simulation methods (to be called by test script)
    def simulate_speech(self, text: str):
        if self._callback and self.is_running:
            evt = STTEvent(
                reason=STTResultReason.RECOGNIZED_SPEECH,
                text=text,
                duration=1.5
            )
            self._callback(evt)
    
    def write(self, data: bytes):
        pass # Mock writing

class MockSTTProvider(STTProvider):
    def create_recognizer(self, language: str = "es-MX", audio_mode: str = "twilio", on_interruption_callback=None, event_loop=None) -> Any:
        print(f"🛠️ [MOCK STT] Creating Recognizer (Lang={language}, Mode={audio_mode})")
        recognizer = MockRecognizer()
        return recognizer

    async def stop_recognition(self):
        print("🛠️ [MOCK STT] Stopping")

# --- MOCK LLM ---

class MockLLMProvider(LLMProvider):
    async def get_stream(self, messages: list, system_prompt: str, temperature: float, max_tokens: int = 600, model: Optional[str] = None) -> AsyncGenerator[str, None]:
        print(f"🛠️ [MOCK LLM] Generating for {len(messages)} messages (Model={model})")
        # Simulate thinking
        await asyncio.sleep(0.1)
        response = "Respuesta simulada del sistema."
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.01)

# --- MOCK TTS ---

class MockSynthesizer:
    pass

class MockTTSProvider(TTSProvider):
    def create_synthesizer(self, voice_name: str, audio_mode: str = "twilio") -> Any:
        print(f"🛠️ [MOCK TTS] Creating Synthesizer (Voice={voice_name}, Mode={audio_mode})")
        return MockSynthesizer()

    async def synthesize_ssml(self, synthesizer: Any, ssml: str) -> bytes:
        print(f"🛠️ [MOCK TTS] Synthesizing SSML: {ssml[:50]}...")
        await asyncio.sleep(0.1)
        return b'\x00\x01' * 1600 # Dummy audio bytes
