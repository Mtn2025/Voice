"""
Provider Registry - Config-driven adapter selection.

Extensible registry pattern for voice AI providers.
Configured via environment variables (Coolify-compatible).
"""
import logging
from collections.abc import Callable

from app.domain.ports import LLMPort, STTPort, TTSPort
from app.domain.ports.provider_config import LLMProviderConfig, STTProviderConfig, TTSProviderConfig

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for voice AI provider factories.

    Enables config-driven provider selection without modifying code.
    New providers can be added by:
    1. Creating adapter class
    2. Registering factory function
    3. Setting ENV var (e.g., DEFAULT_STT_PROVIDER=deepgram)
    """

    def __init__(self):
        self._stt_factories: dict[str, Callable[[STTProviderConfig], STTPort]] = {}
        self._llm_factories: dict[str, Callable[[LLMProviderConfig], LLMPort]] = {}
        self._tts_factories: dict[str, Callable[[TTSProviderConfig], TTSPort]] = {}

    # -------------------------------------------------------------------------
    # Registration Methods
    # -------------------------------------------------------------------------

    def register_stt(self, provider_name: str, factory_fn: Callable):
        """Register STT provider factory."""
        self._stt_factories[provider_name] = factory_fn
        logger.debug(f"✅ [Registry] Registered STT provider: {provider_name}")

    def register_llm(self, provider_name: str, factory_fn: Callable):
        """Register LLM provider factory."""
        self._llm_factories[provider_name] = factory_fn
        logger.debug(f"✅ [Registry] Registered LLM provider: {provider_name}")

    def register_tts(self, provider_name: str, factory_fn: Callable):
        """Register TTS provider factory."""
        self._tts_factories[provider_name] = factory_fn
        logger.debug(f"✅ [Registry] Registered TTS provider: {provider_name}")

    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------

    def create_stt(self, config: STTProviderConfig) -> STTPort:
        """
        Create STT adapter from config.

        Args:
            config: STT provider configuration

        Returns:
            STTPort implementation

        Raises:
            ValueError: If provider not registered
        """
        if config.provider not in self._stt_factories:
            available = ", ".join(self._stt_factories.keys())
            raise ValueError(
                f"Unknown STT provider: '{config.provider}'. "
                f"Available: {available}"
            )

        factory = self._stt_factories[config.provider]
        logger.info(f"🏭 [Registry] Creating STT adapter: {config.provider}")
        return factory(config)

    def create_llm(self, config: LLMProviderConfig) -> LLMPort:
        """Create LLM adapter from config."""
        if config.provider not in self._llm_factories:
            available = ", ".join(self._llm_factories.keys())
            raise ValueError(
                f"Unknown LLM provider: '{config.provider}'. "
                f"Available: {available}"
            )

        factory = self._llm_factories[config.provider]
        logger.info(f"🏭 [Registry] Creating LLM adapter: {config.provider}")
        return factory(config)

    def create_tts(self, config: TTSProviderConfig) -> TTSPort:
        """Create TTS adapter from config."""
        if config.provider not in self._tts_factories:
            available = ", ".join(self._tts_factories.keys())
            raise ValueError(
                f"Unknown TTS provider: '{config.provider}'. "
                f"Available: {available}"
            )

        factory = self._tts_factories[config.provider]
        logger.info(f"🏭 [Registry] Creating TTS adapter: {config.provider}")
        return factory(config)

    # -------------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------------

    def get_available_providers(self) -> dict:
        """Get list of registered providers."""
        return {
            'stt': list(self._stt_factories.keys()),
            'llm': list(self._llm_factories.keys()),
            'tts': list(self._tts_factories.keys())
        }


# Global registry instance
_registry = ProviderRegistry()


def get_provider_registry() -> ProviderRegistry:
    """Get global provider registry."""
    return _registry
