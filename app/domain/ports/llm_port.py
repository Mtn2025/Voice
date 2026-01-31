"""
Puerto (Interface) para proveedores de Large Language Models (LLM).

Define el contrato para integración de modelos de lenguaje.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Mensaje en conversación."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMRequest:
    """Solicitud de generación LLM."""
    messages: list[LLMMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int = 600
    system_prompt: str | None = None
    tools: list | None = None
    metadata: dict = None

    # Advanced LLM Controls
    frequency_penalty: float | None = 0.0
    presence_penalty: float | None = 0.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMPort(ABC):
    """
    Puerto para proveedores de LLM.
    """

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> 'AsyncIterator':
        """
        Genera respuesta en modo streaming.

        Args:
            request: Parámetros de generación

        Yields:
            LLMChunk con text o function_call

        Raises:
            LLMException: Si falla la generación
        """
        pass

    @abstractmethod
    async def get_available_models(self) -> list[str]:
        """
        Obtiene lista de modelos disponibles.

        Returns:
            Lista de IDs de modelos
        """
        pass

    @abstractmethod
    def is_model_safe_for_voice(self, model: str) -> bool:
        """
        Verifica si un modelo es seguro para voz.

        Args:
            model: ID del modelo

        Returns:
            True si es seguro para voz
        """
        pass


class LLMException(Exception):  # noqa: N818 - Domain naming, consistent
    """
    Excepción base para errores de LLM.

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
