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
    
    # Provider-specific overlays
    silence_timeout_ms_phone: Optional[int] = None
    silence_timeout_ms_telnyx: Optional[int] = None


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
