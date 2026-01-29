from collections.abc import AsyncGenerator

from groq import AsyncGroq

from app.core.config import settings


class LLMService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        # Using Llama 3.3 70B - safest and fastest option for voice assistant
        # Does NOT generate <think> tags, excellent for Spanish, no reasoning artifacts
        self.model = "llama-3.3-70b-versatile"

    async def get_chat_stream(self, messages: list) -> AsyncGenerator[str, None]:
        """
        Streams response from LLM.
        """
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.6,
            max_tokens=256,
            top_p=1,
            stream=True,
            stop=None,
        )

        async for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

llm_service = LLMService()
