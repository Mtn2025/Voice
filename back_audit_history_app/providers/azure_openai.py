import logging
import json
import hashlib
from collections.abc import AsyncGenerator
from openai import AsyncAzureOpenAI
from app.core.config import settings
from app.services.base import AbstractLLM
from app.core.redis_state import redis_state

class AzureOpenAIProvider(AbstractLLM):
    def __init__(self):
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        
        if not self.api_key or not self.endpoint:
            logging.warning("⚠️ Azure OpenAI Credentials missing. Provider may fail.")

        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )

    async def get_stream(self, messages: list, system_prompt: str, temperature: float, 
                         max_tokens: int = 600, model: str | None = None) -> AsyncGenerator[str, None]:
        """
        Stream completion from Azure OpenAI.
        Note: 'model' arg is usually ignored in Azure in favor of 'deployment_name'.
        """
        # Ensure correct message format
        chat_messages = [{"role": "system", "content": system_prompt}] + [m for m in messages if m["role"] != "system"]

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,  # In Azure, model = deployment name
                messages=chat_messages,
                temperature=temperature,
                max_tokens=max_tokens,  # ✅ Now accepts as parameter
                stop=["User:", "System:", "\n\nUser", "\n\nSystem"],
                stream=True
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logging.error(f"❌ Azure OpenAI Error: {e}")
            yield "Lo siento, hubo un error de conexión con mi cerebro en la nube."

    async def extract_data(self, transcript: str, model: str = "gpt-4o-mini"):
        """
        Analyzes the transcript and extracts structured data using JSON Mode.
        Compatible with GroqProvider interface.
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

        # 1. Check Cache
        transcript_hash = hashlib.md5(transcript.encode()).hexdigest()
        cache_key = f"extraction:{transcript_hash}"
        cached = await redis_state.cache_get(cache_key)

        if cached:
            logging.info(f"⚡ [CACHE] Extraction hit for hash {transcript_hash[:8]}")
            return cached

        try:
            completion = await self.client.chat.completions.create(
                model=self.deployment_name,  # Use configured deployment
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transcript:\n{transcript}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)

            # 2. Store in Cache (24h)
            await redis_state.cache_set(cache_key, result, ttl=86400)

            return result
        except Exception as e:
            logging.error(f"Extraction Error: {e}")
            return {"error": str(e)}

    async def transcribe_audio(self, audio_content: bytes, language: str = "es") -> str:
        # Azure OpenAI Whisper not implemented here (usually specific endpoint). 
        # Fallback or use standard Whisper if needed. 
        # For now, Orchestrator handles STT via Azure Speech SDK or Groq.
        return ""
