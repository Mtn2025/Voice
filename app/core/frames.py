from dataclasses import dataclass, field
from typing import Any, Dict
import uuid
import time

@dataclass
class Frame:
    """Base class for all frames in the pipeline."""
    id: str = field(init=False)
    name: str = field(init=False)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.id = str(uuid.uuid4())
        self.name = self.__class__.__name__

@dataclass
class SystemFrame(Frame):
    """Frames that have high priority and control the pipeline flow."""
    pass

@dataclass
class DataFrame(Frame):
    """Frames that carry content (audio, text, etc.)."""
    pass

@dataclass
class ControlFrame(Frame):
    """Frames that modify the behavior of processors."""
    pass

@dataclass
class UserStartedSpeakingFrame(SystemFrame):
    pass

@dataclass
class UserStoppedSpeakingFrame(SystemFrame):
    pass

# --- System Frames ---

@dataclass
class StartFrame(SystemFrame):
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EndFrame(SystemFrame):
    reason: str = "normal"

@dataclass
class CancelFrame(SystemFrame):
    reason: str = "cancelled"

@dataclass
class ErrorFrame(SystemFrame):
    error: str
    fatal: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

# --- Data Frames ---

@dataclass
class AudioFrame(DataFrame):
    data: bytes
    sample_rate: int
    channels: int = 1

@dataclass
class TextFrame(DataFrame):
    text: str
    is_final: bool = True

@dataclass
class ImageFrame(DataFrame):
    data: bytes
    format: str
    size: tuple[int, int]

@dataclass
class RMSFrame(DataFrame):
    rms: float


# --- Control Frames ---

@dataclass
class UpdateSettingsFrame(ControlFrame):
    settings: Dict[str, Any]
