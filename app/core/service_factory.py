from app.db.models import AgentConfig
from app.providers.azure import AzureProvider
from app.providers.groq import GroqProvider


class ServiceFactory:
    @staticmethod
    def get_stt_provider(config: AgentConfig):
        if config.stt_provider == "azure":
            return AzureProvider()
        # Add deepgram here later
        return AzureProvider()

    @staticmethod
    def get_tts_provider(config: AgentConfig):
        if config.tts_provider == "azure":
            return AzureProvider()
        return AzureProvider()

    @staticmethod
    def get_llm_provider(config: AgentConfig):
        if config.llm_provider == "groq":
            return GroqProvider()
        return GroqProvider()
