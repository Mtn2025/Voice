"""
Puerto (Interface) para repositorio de configuración.

Abstrae la persistencia de AgentConfig.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ConfigDTO:
    """
    Data Transfer Object para configuración del agente.
    """
    # LLM Config
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.7
    max_tokens: int = 600
    system_prompt: str = ""
    first_message: str = ""
    first_message_mode: str = "text"

    # TTS Config
    tts_provider: str = "azure"
    voice_name: str = "es-MX-DaliaNeural"
    voice_style: str = "default"
    voice_speed: float = 1.0
    voice_language: str = "es-MX"

    # STT Config
    stt_provider: str = "azure"
    stt_language: str = "es-MX"
    silence_timeout_ms: int = 1000

    # Advanced
    enable_denoising: bool = True
    enable_backchannel: bool = False
    max_duration: int = 300

    # Telephony
    twilio_account_sid: str | None = None
    telnyx_api_key: str | None = None
    caller_id_phone: str | None = None
    sip_trunk_uri: str | None = None
    sip_auth_user: str | None = None
    recording_enabled: bool = False
    recording_channels: str = "mono"

    # Function Calling
    tool_server_url: str | None = None
    tool_server_secret: str | None = None
    tools_schema: Any | None = None
    async_tools: bool = False
    tool_timeout_ms: int = 5000

    # Analysis
    analysis_prompt: str | None = None
    success_rubric: str | None = None
    extraction_schema: Any | None = None
    sentiment_analysis: bool = False
    webhook_url: str | None = None
    log_webhook_url: str | None = None

    # System
    concurrency_limit: int = 10
    spend_limit_daily: float = 50.0
    environment: str = "dev"
    privacy_mode: bool = False

    # Provider-specific overlays
    extra_settings_phone: Any | None = None
    extra_settings_telnyx: Any | None = None


class ConfigRepositoryPort(ABC):
    """
    Puerto para persistencia de configuración.
    """

    @abstractmethod
    async def get_config(self, profile: str = "default") -> ConfigDTO:
        """
        Obtiene configuración por perfil.

        Args:
            profile: Perfil de configuración

        Returns:
            DTO con configuración

        Raises:
            ConfigNotFoundException: Si no existe el perfil
        """
        pass

    @abstractmethod
    async def update_config(self, profile: str, **updates) -> ConfigDTO:
        """
        Actualiza configuración.

        Args:
            profile: Perfil a actualizar
            **updates: Campos a actualizar

        Returns:
            ConfigDTO actualizado

        Raises:
            ConfigNotFoundException: Si no existe el perfil
        """
        pass

    @abstractmethod
    async def create_config(self, profile: str, config: ConfigDTO) -> ConfigDTO:
        """
        Crea nueva configuración.

        Args:
            profile: Nombre del perfil
            config: DTO con valores iniciales

        Returns:
            ConfigDTO creado
        """
        pass


class ConfigNotFoundException(Exception):  # noqa: N818 - Domain naming, 50+ refs
    """Error: configuración no encontrada."""
    pass
