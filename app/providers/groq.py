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
        self.default_model = "llama-3.3-70b-versatile"

    async def get_available_models(self):
        try:
            # Dynamic Fetch from Groq API
            # This ensures we always have the latest supported models (no more hardcoded deprecations)
            models = await self.client.models.list()
            # Filter out Whisper/Audio models
            return [m.id for m in models.data if "whisper" not in m.id]
        except Exception as e:
            logging.warning(f"Could not fetch Groq models dynamically: {e}")
            # Fallback list if API fails
            return [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant", 
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

    async def extract_data(self, transcript: str):
        """
        Analyzes the transcript and extracts structured data using JSON Mode.
        """
        system_prompt = (
            "You are a Data Extraction Specialist. Your job is to extract 5 key fields from the call transcript.\n"
            "Return valid JSON ONLY. No markdown, no commentary.\n\n"
            "Fields to extract:\n"
            "- client_name: (string/null) Name of the person spoken to.\n"
            "- interest_level: (string) 'HIGH', 'MEDIUM', 'LOW' or 'NONE'.\n"
            "- appointment_date: (string/null) Date/Time if mentioned (ISO format preferred).\n"
            "- whatsapp_number: (string/null) Phone number if provided.\n"
            "- key_notes: (string) Concise summary of needs or objections."
        )
        
        try:
            completion = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transcript:\n{transcript}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            logging.error(f"Extraction Error: {e}")
            return {"error": str(e)}
