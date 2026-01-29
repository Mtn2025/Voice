"""
DI Container - Dependency Injection Container para arquitectura hexagonal.

Configura y provee instancias de puertos (interfaces) con sus
adaptadores (implementaciones) correspondientes.
"""

import logging
from typing import Optional
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Ports
from app.domain.ports import (
    TTSPort,
    LLMPort,
    STTPort,
    CachePort,
    ConfigRepositoryPort,
    CallRepositoryPort  # ✅ FIX VIOLATION #1
)

# Adapters
from app.adapters.outbound import (
    AzureTTSAdapter,
    GroqLLMAdapter,
    AzureSTTAdapter,
    RedisCacheAdapter,
    PostgresConfigRepository
)
from app.adapters.outbound.persistence.sqlalchemy_call_repository import SQLAlchemyCallRepository  # ✅ FIX VIOLATION #1
from app.db.database import AsyncSessionLocal  # ✅ Only in DI container, not in core!


logger = logging.getLogger(__name__)


class Container(containers.DeclarativeContainer):
    """
    Container de inyección de dependencias.
    
    Centraliza la creación de adaptadores y permite cambiar
    implementaciones sin tocar el dominio.
    """
    
    # Configuration
    config = providers.Configuration()
    
    # Database session (provided externally)
    db_session = providers.Dependency(instance_of=AsyncSession)
    
    # Cache
    cache_adapter = providers.Singleton(
        RedisCacheAdapter
    )
    
    # TTS
    tts_adapter = providers.Factory(
        AzureTTSAdapter,
        audio_mode=config.audio_mode or "twilio"
    )
    
    # LLM - ✅ CHANGED: Singleton → Factory (per-call isolation)
    llm_adapter = providers.Factory(
        GroqLLMAdapter
    )
    
    # STT - ✅ CHANGED: Singleton → Factory (per-call isolation)
    stt_adapter = providers.Factory(
        AzureSTTAdapter
    )
    
    # Config Repository
    config_repository = providers.Factory(
        PostgresConfigRepository,
        session=db_session
    )
    
    # ✅ FIX VIOLATION #1: Call Repository
    call_repository = providers.Factory(
        SQLAlchemyCallRepository,
        session_factory=providers.Object(AsyncSessionLocal)
    )


# Global container instance
container = Container()


def get_tts_port(audio_mode: str = "twilio") -> TTSPort:
    """
    Factory para obtener puerto TTS.
    
    Args:
        audio_mode: "browser", "twilio", "telnyx"
        
    Returns:
        Instancia de TTSPort (actualmente AzureTTSAdapter)
    """
    container.config.audio_mode.from_value(audio_mode)
    return container.tts_adapter()


def get_llm_port() -> LLMPort:
    """
    Factory para obtener puerto LLM.
    
    Returns:
        Instancia de LLMPort (actualmente GroqLLMAdapter)
    """
    return container.llm_adapter()


def get_stt_port() -> STTPort:
    """
    Factory para obtener puerto STT.
    
    Returns:
        Instancia de STTPort (actualmente AzureSTTAdapter)
    """
    return container.stt_adapter()


def get_cache_port() -> CachePort:
    """
    Factory para obtener puerto de cache.
    
    Returns:
        Instancia de CachePort (actualmente RedisCacheAdapter)
    """
    return container.cache_adapter()


def get_config_repository(session: AsyncSession) -> ConfigRepositoryPort:
    """
    Factory para obtener repositorio de configuración.
    
    Args:
        session: Sesión de SQLAlchemy activa
        
    Returns:
        Instancia de ConfigRepositoryPort
    """
    container.db_session.override(session)
    return container.config_repository()


# Convenience functions for testing/mocking
def override_tts_adapter(adapter_class):
    """Override TTS adapter (for testing)."""
    container.tts_adapter.override(providers.Factory(adapter_class))


def override_llm_adapter(adapter_class):
    """Override LLM adapter (for testing)."""
    container.llm_adapter.override(providers.Factory(adapter_class))


def override_stt_adapter(adapter_class):
    """Override STT adapter (for testing)."""
    container.stt_adapter.override(providers.Factory(adapter_class))


def reset_overrides():
    """Reset all overrides (restore production adapters)."""
    container.reset_singletons()
    container.reset_last_overriding()


logger.info("✅ [DI Container] Initialized with Azure TTS, Groq LLM, Azure STT, Redis Cache")
