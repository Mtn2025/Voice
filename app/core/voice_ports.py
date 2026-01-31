"""
Voice Ports Factory - Config-driven provider instantiation.

✅ Hexagonal Architecture: Factory constructs clean config objects
✅ Open/Closed Principle: Provider selection via ENV vars (no code changes)
✅ Coolify-Compatible: All config from environment variables
"""
import logging

from app.adapters.outbound.llm.groq_llm_adapter import GroqLLMAdapter
from app.adapters.outbound.llm.llm_with_fallback import LLMWithFallback
from app.adapters.outbound.persistence.sqlalchemy_call_repository import SQLAlchemyCallRepository
from app.adapters.outbound.repositories.sqlalchemy_config_repository import (
    SQLAlchemyConfigRepository,
)

# Adapters
from app.adapters.outbound.stt.azure_stt_adapter import AzureSTTAdapter
from app.adapters.outbound.stt.google_stt_adapter import GoogleSTTAdapter
from app.adapters.outbound.stt.stt_with_fallback import STTWithFallback
from app.adapters.outbound.tts.azure_tts_adapter import AzureTTSAdapter
from app.adapters.outbound.tts.google_tts_adapter import GoogleTTSAdapter
from app.adapters.outbound.tts.tts_with_fallback import TTSWithFallback
from app.core.adapter_registry import AdapterRegistry
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.domain.ports import CallRepositoryPort, ConfigRepositoryPort, LLMPort, STTPort, TTSPort
from app.domain.ports.provider_config import LLMProviderConfig, STTProviderConfig, TTSProviderConfig
from app.infrastructure.provider_registry import get_provider_registry

logger = logging.getLogger(__name__)


class VoicePorts:
    """
    Container for Voice AI Ports (Hexagonal Architecture).

    Provides STT, LLM, TTS, Config Repository, and Tool adapters implementing domain ports.

    ✅ P4: Includes AdapterRegistry for runtime adapter swapping.
    """
    def __init__(
        self,
        stt: STTPort,
        llm: LLMPort,
        tts: TTSPort,
        config_repo: ConfigRepositoryPort,
        call_repo: CallRepositoryPort,
        tools: dict | None = None,
        registry = None
    ):
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.config_repo = config_repo
        self.call_repo = call_repo
        self.tools = tools or {}
        self.registry = registry


def _register_providers():
    """
    ✅ Register all available providers in global registry.

    New providers can be added here without touching voice_ports factory.
    """
    registry = get_provider_registry()

    # STT Providers
    registry.register_stt('azure', lambda cfg: AzureSTTAdapter(config=cfg))
    registry.register_stt('google', lambda cfg: GoogleSTTAdapter(credentials_path=None))

    # LLM Providers
    registry.register_llm('groq', lambda cfg: GroqLLMAdapter(config=cfg))

    # TTS Providers
    registry.register_tts('azure', lambda cfg: AzureTTSAdapter(config=cfg))
    registry.register_tts('google', lambda cfg: GoogleTTSAdapter(credentials_path=None))

    logger.info("✅ [VoicePorts] Providers registered in global registry")


def get_voice_ports(audio_mode: str = "twilio") -> VoicePorts:
    """
    ✅ Config-Driven Factory: Get voice AI ports from ENV configuration.

    Provider selection via environment variables (Coolify-compatible):
    - DEFAULT_STT_PROVIDER=azure|google
    - DEFAULT_LLM_PROVIDER=groq|openai|gemini
    - DEFAULT_TTS_PROVIDER=azure|google|elevenlabs

    Args:
        audio_mode: "browser", "twilio", "telnyx" (for TTS format)

    Returns:
        VoicePorts container with configured adapters

    Example (Coolify ENV vars):
        ```env
        DEFAULT_STT_PROVIDER=azure
        AZURE_SPEECH_KEY=xxxxx
        AZURE_SPEECH_REGION=eastus
        ```
    """
    # ✅ Register providers (idempotent)
    _register_providers()

    registry = get_provider_registry()

    # -------------------------------------------------------------------------
    # ✅ STT Adapter (Config-driven from ENV)
    # -------------------------------------------------------------------------
    stt_provider_name = settings.DEFAULT_STT_PROVIDER

    stt_config = STTProviderConfig(
        provider=stt_provider_name,
        api_key=settings.AZURE_SPEECH_KEY if stt_provider_name == 'azure' else "",
        region=settings.AZURE_SPEECH_REGION if stt_provider_name == 'azure' else None,
        language="es-MX",
        sample_rate=8000
    )

    primary_stt = registry.create_stt(stt_config)

    # Fallback STT (Google)
    fallback_stt = GoogleSTTAdapter(credentials_path=None)

    stt_adapter = STTWithFallback(primary=primary_stt, fallback=fallback_stt)
    logger.info(f"✅ [VoicePorts] STT configured: {stt_provider_name} → google (fallback)")

    # -------------------------------------------------------------------------
    # ✅ LLM Adapter (Config-driven from ENV)
    # -------------------------------------------------------------------------
    llm_provider_name = settings.DEFAULT_LLM_PROVIDER

    llm_config = LLMProviderConfig(
        provider=llm_provider_name,
        api_key=settings.GROQ_API_KEY if llm_provider_name == 'groq' else "",
        model=settings.GROQ_MODEL if llm_provider_name == 'groq' else "llama-3.3-70b-versatile",
        temperature=0.7
    )

    primary_llm = registry.create_llm(llm_config)

    # Fallbacks (future: OpenAI, Claude)
    llm_adapter = LLMWithFallback(primary=primary_llm, fallbacks=[])
    logger.info(f"✅ [VoicePorts] LLM configured: {llm_provider_name}")

    # -------------------------------------------------------------------------
    # ✅ TTS Adapter (Config-driven from ENV)
    # -------------------------------------------------------------------------
    tts_provider_name = settings.DEFAULT_TTS_PROVIDER

    tts_config = TTSProviderConfig(
        provider=tts_provider_name,
        api_key=settings.AZURE_SPEECH_KEY if tts_provider_name == 'azure' else "",
        region=settings.AZURE_SPEECH_REGION if tts_provider_name == 'azure' else None,
        audio_mode=audio_mode
    )

    primary_tts = registry.create_tts(tts_config)

    # Fallback TTS (Google)
    fallback_tts = GoogleTTSAdapter(credentials_path=None)

    tts_adapter = TTSWithFallback(primary=primary_tts, fallback=fallback_tts)
    logger.info(f"✅ [VoicePorts] TTS configured: {tts_provider_name} → google (fallback)")

    # -------------------------------------------------------------------------
    # ✅ Adapter Registry (P4: Runtime swapping)
    # -------------------------------------------------------------------------
    adapter_registry = AdapterRegistry()
    adapter_registry.register("stt_primary", primary_stt)
    adapter_registry.register("stt_fallback", fallback_stt)
    adapter_registry.register("llm_primary", primary_llm)
    adapter_registry.register("tts_primary", primary_tts)
    adapter_registry.register("tts_fallback", fallback_tts)

    # -------------------------------------------------------------------------
    # ✅ Config Repository
    # -------------------------------------------------------------------------
    config_repo = SQLAlchemyConfigRepository(session_factory=AsyncSessionLocal)

    # -------------------------------------------------------------------------
    # ✅ Call Repository
    # -------------------------------------------------------------------------
    call_repo = SQLAlchemyCallRepository(session_factory=AsyncSessionLocal)

    # -------------------------------------------------------------------------
    # ✅ Tool Calling Infrastructure
    # -------------------------------------------------------------------------
    tools = {}

    try:
        from app.adapters.outbound.tools.database_tool_adapter import DatabaseToolAdapter
        db_tool = DatabaseToolAdapter(session_factory=AsyncSessionLocal)
        tools[db_tool.name] = db_tool
        logger.info(f"🔧 [VoicePorts] Registered tool: {db_tool.name}")
    except Exception as e:
        logger.warning(f"⚠️ [VoicePorts] Failed to register DatabaseTool: {e}")

    logger.info("✅ [VoicePorts] All ports initialized (config-driven, Coolify-compatible)")

    return VoicePorts(
        stt=stt_adapter,
        llm=llm_adapter,
        tts=tts_adapter,
        config_repo=config_repo,
        call_repo=call_repo,
        tools=tools,
        registry=adapter_registry
    )



