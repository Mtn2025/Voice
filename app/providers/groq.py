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
        self.api_key = settings.GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.api_key)
        self.default_model = "deepseek-r1-distill-llama-70b"

    def get_available_models(self):
        return [
            "deepseek-r1-distill-llama-70b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "mixtral-8x7b-32768"
        ]

    async def get_stream(self, messages: list, system_prompt: str, temperature: float, model: str = None) -> AsyncGenerator[str, None]:
        
        target_model = model or self.default_model

        # Ensure correct message format for Groq
        chat_messages = [{"role": "system", "content": system_prompt}] + [m for m in messages if m["role"] != "system"]
        
        try:
            completion = await self.client.chat.completions.create(
                model=target_model,
                messages=chat_messages,
                temperature=temperature,
                max_tokens=600, # Increased for DeepSeek reasoning if needed
                stream=True
            )

            async for chunk in completion:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logging.error(f"Groq Error ({target_model}): {e}")
            yield f"Error: {str(e)}"

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
