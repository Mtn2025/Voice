from groq import AsyncGroq
from app.services.base import AbstractLLM
from app.core.config import settings
from typing import AsyncGenerator
import io
import json
import base64
import logging

class GroqProvider(AbstractLLM):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        # Default model, can be overridden by config usually, but Groq requires specific model names
        self.model_map = {
            "default": "llama-3.3-70b-versatile",
            "deepseek": "deepseek-r1-distill-llama-70b" 
        }

    async def get_stream(self, messages: list, system_prompt: str, temperature: float) -> AsyncGenerator[str, None]:
        # Inject system prompt if not present or replace it?
        # Typically orchestrator manages history. We ensure system prompt is first.
        
        msgs = [{"role": "system", "content": system_prompt}] + [m for m in messages if m["role"] != "system"]
        
        completion = await self.client.chat.completions.create(
            model=self.model_map.get("default"), # Could be dynamic
            messages=msgs,
            temperature=temperature,
            max_tokens=512,
            stream=True
        )

        async for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def transcribe_audio(self, audio_content: bytes, language: str = "es") -> str:
        """
        Transcribes audio using Groq Whisper (faster/better than Azure Realtime often).
        """
        try:
            # Create a file-like object
            audio_file = io.BytesIO(audio_content)
            audio_file.name = "audio.wav" # Groq needs a filename
            
            transcription = await self.client.audio.transcriptions.create(
                file=(audio_file.name, audio_file.read()),
                model="whisper-large-v3",
                response_format="json",
                language=language,
                temperature=0.0
            )
            return transcription.text
        except Exception as e:
            print(f"Groq STT Error: {e}")
            return ""
