from app.db.models import AgentConfig
from app.providers.azure import AzureProvider
from app.providers.groq import GroqProvider
from app.providers.azure_openai import AzureOpenAIProvider


class ServiceFactory:
    @staticmethod
    def get_stt_provider(config: AgentConfig):
        if config.stt_provider == "azure":
            return AzureProvider()
        return AzureProvider()

    @staticmethod
    def get_tts_provider(config: AgentConfig):
        if config.tts_provider == "azure":
            return AzureProvider()
        return AzureProvider()

    @staticmethod
    def get_llm_provider(config: AgentConfig):
        provider_name = (config.llm_provider or "").lower()
        
        if provider_name == "azure" or provider_name == "azure openai":
            return AzureOpenAIProvider()
        
        if provider_name == "groq" or not provider_name:
            return GroqProvider()
            
        # Fallback/Error? For now default to Groq as safeguard
        # but we could log warning.
        import logging
        logging.warning(f"⚠️ Unknown LLM Provider '{provider_name}'. Defaulting to Groq.")
        return GroqProvider()
