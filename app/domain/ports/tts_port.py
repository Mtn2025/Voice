"""
Puerto (Interface) para proveedores de Text-to-Speech (TTS).

Define el contrato que deben cumplir todos los adaptadores TTS
para integrarse con el dominio.
"""

from abc import ABC, abstractmethod
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

    Generic parameters work with all TTS providers.
    Vendor-specific options go in provider_options dict.
    """
    text: str
    voice_id: str
    language: str = "es-MX"

    # Generic parameters
    pitch: int = 0
    speed: float = 1.0
    volume: float = 100.0
    format: str = "pcm_16000"
    style: str = None
    backpressure_detected: bool = False

    # Provider-specific options
    provider_options: dict = None

    # Metadata
    metadata: dict = None

    def __post_init__(self):
        """Initialize default dicts if None."""
        if self.provider_options is None:
            self.provider_options = {}
        if self.metadata is None:
            self.metadata = {}


class TTSPort(ABC):
    """
    Puerto para proveedores de Text-to-Speech.
    """

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> bytes:
        """
        Sintetiza texto a audio.

        Args:
            request: Parámetros de síntesis

        Returns:
            Audio en bytes

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
    def get_available_voices(self, language: str | None = None) -> list[VoiceMetadata]:
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


class TTSException(Exception):  # noqa: N818 - Domain naming, consistent
    """
    Excepción base para errores de TTS.

    Attributes:
        message: Mensaje de error humanizado
        retryable: Si el error puede resolverse reintentando
        provider: Proveedor que generó el error
        original_error: Excepción original del SDK
    """

    def __init__(
        self,
        message: str,
        retryable: bool = False,
        provider: str = "unknown",
        original_error: Exception | None = None
    ):
        super().__init__(message)
        self.retryable = retryable
        self.provider = provider
        self.original_error = original_error

    def __str__(self):
        retry_hint = "(retryable)" if self.retryable else "(not retryable)"
        return f"[{self.provider}] {super().__str__()} {retry_hint}"
