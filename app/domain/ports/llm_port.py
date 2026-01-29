"""
Puerto (Interface) para proveedores de Large Language Models (LLM).

Define el contrato para integración de modelos de lenguaje como
Groq, Azure OpenAI, Anthropic, etc.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
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
    system_prompt: Optional[str] = None
    tools: Optional[list] = None  # ✅ Module 9: Tool definitions for function calling
    metadata: dict = None  # ✅ trace_id, etc.
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMPort(ABC):
    """
    Puerto para proveedores de LLM.
    
    Implementaciones: GroqAdapter, AzureOpenAIAdapter, AnthropicAdapter
    """
    
    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> 'AsyncIterator[LLMChunk]':
        """
        Genera respuesta en modo streaming.
        
        ✅ Module 9: Returns LLMChunk (supports text + function_call)
        
        Args:
            request: Parámetros de generación (incluye tools para function calling)
            
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
        
        Modelos con razonamiento (deepseek-r1, etc.) generan tags
        <think> que no deben verbalizarse.
        
        Args:
            model: ID del modelo
            
        Returns:
            True si es seguro para voz
        """
        pass


class LLMException(Exception):
    """
    Excepción base para errores de LLM.
    
    Attributes:
        message: Mensaje de error humanizado
        retryable: Si el error puede resolverse reintentando
        provider: Proveedor que generó el error ("groq", "openai", etc.)
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
