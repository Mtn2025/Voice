import logging
from collections.abc import AsyncGenerator
from openai import AsyncAzureOpenAI
from app.core.config import settings
from app.services.base import AbstractLLM

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

    async def get_stream(self, messages: list, system_prompt: str, temperature: float, model: str | None = None) -> AsyncGenerator[str, None]:
        # Note: 'model' arg is usually ignored in Azure in favor of 'deployment_name', 
        # but some setups invoke deployments by model name. We'll use the configured deployment.
        
        # Ensure correct message format
        chat_messages = [{"role": "system", "content": system_prompt}] + [m for m in messages if m["role"] != "system"]

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name, # In Azure, model = deployment name
                messages=chat_messages,
                temperature=temperature,
                max_tokens=600,
                stream=True
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logging.error(f"❌ Azure OpenAI Error: {e}")
            yield "Lo siento, hubo un error de conexión con mi cerebro en la nube."

    async def transcribe_audio(self, audio_content: bytes, language: str = "es") -> str:
        # Azure OpenAI Whisper not implemented here (usually specific endpoint). 
        # Fallback or use standard Whisper if needed. 
        # For now, Orchestrator handles STT via Azure Speech SDK or Groq.
        return ""
