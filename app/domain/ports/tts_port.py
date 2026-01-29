"""
Puerto (Interface) para proveedores de Text-to-Speech (TTS).

Define el contrato que deben cumplir todos los adaptadores TTS
para integrarse con el dominio de manera desacoplada.
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
from dataclasses import dataclass


@dataclass
class VoiceMetadata:
    """Metadata de una voz disponible."""
    id: str
    name: str
    gender: str
    locale: str


@dataclass
class TTSRequest:
    """
    Voice synthesis request (Domain Model).
    
    ✅ FIX VIOLATION #3: Provider-agnostic design
    Generic parameters work with all TTS providers.
    Vendor-specific options go in provider_options dict.
    """
    text: str
    voice_id: str
    language: str = "es-MX"
    
    # ✅ Generic parameters (work with all providers)
    speed: float = 1.0  # 0.5-2.0 (50% to 200%)
    volume: float = 100.0  # 0-100 (percentage)
    
    # ✅ Provider-specific options (extensible dict)
    provider_options: dict = None  # Azure: {'pitch_hz': 50, 'style': 'cheerful', 'styledegree': 1.5}
                                    # ElevenLabs: {'stability': 0.5, 'similarity_boost': 0.75}
                                    # Google: {'pitch_semitones': 5, 'speaking_rate': 1.2}
    
    # ✅ Metadata (trace_id, backpressure flags, etc.)
    metadata: dict = None
    
    def __post_init__(self):
        """Initialize default dicts if None."""
        if self.provider_options is None:
            self.provider_options = {}
        if self.metadata is None:
            self.metadata = {}
    
    # ✅ BACKWARDS COMPATIBLE: Accessor for legacy code
    @property
    def backpressure_detected(self) -> bool:
        """Check if backpressure is detected (from metadata)."""
        return self.metadata.get('backpressure_detected', False)
    
    @property
    def pitch(self) -> float:
        """Get pitch from provider_options (Azure-specific, backwards compatible)."""
        return self.provider_options.get('pitch_hz', 0.0)
    
    @property
    def style(self) -> Optional[str]:
        """Get style from provider_options (Azure-specific, backwards compatible)."""
        return self.provider_options.get('style')


class TTSPort(ABC):
    """
    Puerto para proveedores de Text-to-Speech.
    
    Implementaciones: AzureTTSAdapter, ElevenLabsAdapter (futuro)
    """
    
    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> bytes:
        """
        Sintetiza texto a audio.
        
        Args:
            request: Parámetros de síntesis
            
        Returns:
            Audio en bytes (formato depende del adaptador/modo)
            
        Raises:
            TTSException: Si falla la síntesis
        """
        pass
    
    @abstractmethod
    async def synthesize_ssml(self, ssml: str) -> bytes:
        """
        Sintetiza directamente desde SSML.
        
        Args:
            ssml: Marcado SSML completo
            
        Returns:
            Audio en bytes
        """
        pass
    
    @abstractmethod
    def get_available_voices(self, language: Optional[str] = None) -> list[VoiceMetadata]:
        """
        Obtiene lista de voces disponibles.
        
        Args:
            language: Filtrar por idioma (opcional)
            
        Returns:
            Lista de metadata de voces
        """
        pass
    
    @abstractmethod
    def get_voice_styles(self, voice_id: str) -> list[str]:
        """
        Obtiene estilos disponibles para una voz.
        
        Args:
            voice_id: ID de la voz
            
        Returns:
            Lista de estilos soportados
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Limpia recursos del provider."""
        pass


class TTSException(Exception):
    """
    Excepción base para errores de TTS.
    
    Attributes:
        message: Mensaje de error humanizado
        retryable: Si el error puede resolverse reintentando
        provider: Proveedor que generó el error ("azure", "elevenlabs")
        original_error: Excepción original del SDK (para debugging)
    """
    
    def __init__(
        self, 
        message: str, 
        retryable: bool = False, 
        provider: str = "unknown",
        original_error: Exception = None
    ):
        super().__init__(message)
        self.retryable = retryable
        self.provider = provider
        self.original_error = original_error
        
    def __str__(self):
        retry_hint = "(retryable)" if self.retryable else "(not retryable)"
        return f"[{self.provider}] {super().__str__()} {retry_hint}"
