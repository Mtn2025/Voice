"""
Puerto (Interface) para proveedores de Speech-to-Text (STT).

Define el contrato para transcripción de audio en tiempo real
compatible con Azure, Groq Whisper, Deepgram, etc.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass


class STTResultReason(Enum):
    """Razón del resultado STT."""
    RECOGNIZED_SPEECH = "recognized"
    RECOGNIZING_SPEECH = "recognizing"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


@dataclass
class STTEvent:
    """Evento de reconocimiento STT."""
    reason: STTResultReason
    text: str
    duration: float = 0.0
    error_details: Optional[str] = None


@dataclass
class STTConfig:
    """Configuración para reconocimiento STT (Base + Advanced)."""
    language: str = "es-MX"
    audio_mode: str = "twilio"  # "twilio", "telnyx", "browser"
    initial_silence_ms: int = 5000
    segmentation_silence_ms: int = 1000
    
    # Advanced Controls (Phase III)
    model: str = "default"
    keywords: Optional[list] = None # [{"word": "Ubrokers", "boost": 2.0}]
    silence_timeout: int = 500
    utterance_end_strategy: str = "default"
    
    # Formatting & Filters
    punctuation: bool = True
    profanity_filter: bool = True
    smart_formatting: bool = True
    
    # Features
    diarization: bool = False
    multilingual: bool = False


class STTRecognizer(ABC):
    """
    Interface para recognizer STT en streaming.
    
    Abstracción sobre Azure SpeechRecognizer, Groq/Deepgram streams, etc.
    """
    
    @abstractmethod
    def subscribe(self, callback: Callable[[STTEvent], None]):
        """
        Suscribe callback para eventos de reconocimiento.
        
        Args:
            callback: Función a llamar con cada STTEvent
        """
        pass
    
    @abstractmethod
    async def start_continuous_recognition(self):
        """Inicia reconocimiento continuo."""
        pass
    
    @abstractmethod
    async def stop_continuous_recognition(self):
        """Detiene reconocimiento continuo."""
        pass
    
    @abstractmethod
    def write(self, audio_data: bytes):
        """
        Escribe datos de audio al stream.
        
        Args:
            audio_data: Bytes de audio (formato según config)
        """
        pass


class STTPort(ABC):
    """
    Puerto para proveedores de Speech-to-Text.
    
    Implementaciones: AzureSTTAdapter, GroqWhisperAdapter, DeepgramAdapter
    """
    
    @abstractmethod
    def create_recognizer(
        self,
        config: STTConfig,
        on_interruption_callback: Optional[Callable] = None,
        event_loop: Optional[Any] = None
    ) -> STTRecognizer:
        """
        Crea un recognizer configurado.
        
        Args:
            config: Configuración STT
            on_interruption_callback: Callback para barge-in (opcional)
            event_loop: Event loop asyncio (opcional)
            
        Returns:
            Instancia de STTRecognizer
        """
        pass
    
    @abstractmethod
    async def transcribe_audio(self, audio_bytes: bytes, language: str = "es") -> str:
        """
        Transcribe audio completo (no streaming).
        
        Args:
            audio_bytes: Audio en bytes
            language: Código de idioma
            
        Returns:
            Texto transcrito
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Limpia recursos del provider."""
        pass


class STTException(Exception):
    """
    Excepción base para errores de STT.
    
    Attributes:
        message: Mensaje de error humanizado
        retryable: Si el error puede resolverse reintentando
        provider: Proveedor que generó el error ("azure", "groq", "deepgram")
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
