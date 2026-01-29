"""
Puerto (Interface) para repositorio de configuración.

Abstrae la persistencia de AgentConfig para desacoplar
el dominio de PostgreSQL, SQLite, o cualquier otra BD.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class ConfigDTO:
    """
    Data Transfer Object para configuración del agente.
    
    Representa el subconjunto de campos relevantes del dominio,
    sin acoplar a SQLAlchemy models.
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
    
    # --- PHASE V: TELEPHONY ---
    twilio_account_sid: Optional[str] = None
    telnyx_api_key: Optional[str] = None
    caller_id_phone: Optional[str] = None
    sip_trunk_uri: Optional[str] = None
    sip_auth_user: Optional[str] = None
    recording_enabled: bool = False
    recording_channels: str = "mono"
    
    # --- PHASE VI: FUNCTION CALLING ---
    tool_server_url: Optional[str] = None
    tool_server_secret: Optional[str] = None
    tools_schema: Optional[Any] = None
    async_tools: bool = False
    tool_timeout_ms: int = 5000
    
    # --- PHASE VII: ANALYSIS ---
    analysis_prompt: Optional[str] = None
    success_rubric: Optional[str] = None
    extraction_schema: Optional[Any] = None
    sentiment_analysis: bool = False
    webhook_url: Optional[str] = None
    log_webhook_url: Optional[str] = None
    
    # --- PHASE VIII: SYSTEM (Safe) ---
    concurrency_limit: int = 10
    spend_limit_daily: float = 50.0
    environment: str = "dev"
    privacy_mode: bool = False
    
    # Provider-specific overlays (Generic Map for Extensibility)
    extra_settings_phone: Optional[Any] = None
    extra_settings_telnyx: Optional[Any] = None


class ConfigRepositoryPort(ABC):
    """
    Puerto para persistencia de configuración.
    
    Implementaciones: PostgresConfigRepository, SQLiteConfigRepository
    """
    
    @abstractmethod
    async def get_config(self, profile: str = "default") -> ConfigDTO:
        """
        Obtiene configuración por perfil.
        
        Args:
            profile: Perfil de configuración ("default", "browser", "twilio", etc.)
            
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


class ConfigNotFoundException(Exception):
    """Error: configuración no encontrada."""
    pass
