"""Value Objects for Voice Configuration (Type-Safe)."""
from dataclasses import dataclass
from typing import Literal

# Type aliases for better readability and type safety
AudioMode = Literal["browser", "twilio", "telnyx"]
VoiceStyle = Literal["default", "cheerful", "sad", "angry", "friendly", "terrified", "excited", "hopeful"]


@dataclass(frozen=True)
class VoiceConfig:
    """
    Immutable voice configuration value object.
    
    Attributes:
        name: Azure voice name (e.g., "es-MX-DaliaNeural")
        speed: Speech rate multiplier (0.5 - 2.0)
        pitch: Pitch offset in Hz (-100 to +100)
        volume: Volume level (0-100)
        style: Speaking style
        style_degree: Style intensity (0.01 - 2.0)
    
    Example:
        >>> config = VoiceConfig(
        ...     name="es-MX-DaliaNeural",
        ...     speed=1.2,
        ...     pitch=5,
        ...     style="friendly"
        ... )
        >>> params = config.to_ssml_params()
    """
    name: str
    speed: float = 1.0
    pitch: int = 0  # Hz offset
    volume: int = 100  # 0-100
    style: VoiceStyle = "default"
    style_degree: float = 1.0  # 0.01-2.0
    
    def validate_voice_config(self):
        """Validate field values (called automatically by __post_init__)."""
        if not (0.5 <= self.speed <= 2.0):
            raise ValueError(f"Speed must be between 0.5 and 2.0, got {self.speed}")
        
        if not (-100 <= self.pitch <= 100):
            raise ValueError(f"Pitch must be between -100 and +100 Hz, got {self.pitch}")
        
        if not (0 <= self.volume <= 100):
            raise ValueError(f"Volume must be between 0 and 100, got {self.volume}")
        
        if not (0.01 <= self.style_degree <= 2.0):
            raise ValueError(f"Style degree must be between 0.01 and 2.0, got {self.style_degree}")
    
    def __post_init__(self):
        """Validate fields after initialization."""
        self.validate_voice_config()
    
    
    @classmethod
    def from_db_config(cls, db_config) -> 'VoiceConfig':
        """
        Factory method to create VoiceConfig from AgentConfig (database model).
        
        Args:
            db_config: SQLAlchemy AgentConfig instance
        
        Returns:
            VoiceConfig: Immutable value object
        
        Example:
            >>> from app.db.models import AgentConfig
            >>> db_config = await get_agent_config(session)
            >>> voice_config = VoiceConfig.from_db_config(db_config)
        """
        return cls(
            name=db_config.voice_name or "es-MX-DaliaNeural",
            speed=float(db_config.voice_speed or 1.0),
            pitch=int(db_config.voice_pitch or 0),
            volume=int(db_config.voice_volume or 100),
            style=db_config.voice_style or "default",
            style_degree=float(db_config.voice_style_degree or 1.0)
        )
    
    def to_ssml_params(self) -> dict:
        """
        Convert to SSML builder parameters.
        
        Returns:
            dict: Parameters ready for build_azure_ssml()
        
        Example:
            >>> config = VoiceConfig(name="es-MX-DaliaNeural", speed=1.2)
            >>> from app.utils.ssml_builder import build_azure_ssml
            >>> ssml = build_azure_ssml(text="Hola", **config.to_ssml_params())
        """
        return {
            "voice_name": self.name,
            "rate": self.speed,
            "pitch": self.pitch,
            "volume": self.volume,
            "style": self.style if self.style != "default" else None,
            "style_degree": self.style_degree if self.style != "default" else None
        }


@dataclass(frozen=True)
class AudioFormat:
    """
    Audio format specification (immutable).
    
    Attributes:
        sample_rate: Sampling rate in Hz (8000, 16000, 24000, etc.)
        channels: Number of audio channels (1=mono, 2=stereo)
        bits_per_sample: Bits per sample (8, 16, 24, 32)
        encoding: Audio encoding format
    
    Example:
        >>> # Twilio/Telnyx format
        >>> telephony_format = AudioFormat(
        ...     sample_rate=8000,
        ...     encoding="mulaw"
        ... )
        >>> assert telephony_format.is_telephony
        
        >>> # Browser format  
        >>> browser_format = AudioFormat(
        ...     sample_rate=16000,
        ...     encoding="pcm"
        ... )
        >>> assert not browser_format.is_telephony
    """
    sample_rate: int  # Hz (8000, 16000, 24000)
    channels: int = 1
    bits_per_sample: int = 16
    encoding: Literal["pcm", "mulaw", "alaw"] = "mulaw"
    
    @property
    def is_telephony(self) -> bool:
        """
        Check if this is telephony format (8kHz mulaw/alaw).
        
        Returns:
            bool: True for Twilio/Telnyx formats
        """
        return self.sample_rate == 8000 and self.encoding in ["mulaw", "alaw"]
    
    @property
    def is_browser(self) -> bool:
        """
        Check if this is browser-compatible format (16kHz PCM).
        
        Returns:
            bool: True for browser WebSocket formats
        """
        return self.sample_rate == 16000 and self.encoding == "pcm"
    
    @classmethod
    def for_client_type(cls, client_type: str) -> 'AudioFormat':
        """
        Factory method to create AudioFormat based on client type.
        
        Args:
            client_type: "browser", "twilio", or "telnyx"
        
        Returns:
            AudioFormat: Appropriate format for client
        
        Example:
            >>> format = AudioFormat.for_client_type("twilio")
            >>> assert format.sample_rate == 8000
            >>> assert format.encoding == "mulaw"
        """
        if client_type == "browser":
            return cls(sample_rate=16000, encoding="pcm")
        elif client_type in ["twilio", "telnyx"]:
            return cls(sample_rate=8000, encoding="mulaw")
        else:
            # Default to telephony format
            return cls(sample_rate=8000, encoding="mulaw")
