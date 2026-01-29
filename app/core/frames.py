from dataclasses import dataclass, field
from typing import Any, Dict
import uuid
import time

@dataclass(kw_only=True)
class Frame:
    """Base class for all frames in the pipeline."""
    id: str = field(init=False)
    name: str = field(init=False)
    timestamp: float = field(default_factory=time.time)
    
    # ✅ Module 3: Distributed Tracing (Gap Analysis #8, #9)
    trace_id: str = field(default="")  # Conversational turn ID
    span_id: str = field(init=False)   # Frame processing span ID
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.id = str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.name = self.__class__.__name__
        
        # Generate trace_id if not provided
        if not self.trace_id:
            self.trace_id = str(uuid.uuid4())

@dataclass(kw_only=True)
class SystemFrame(Frame):
    """Frames that have high priority and control the pipeline flow."""
    pass

@dataclass(kw_only=True)
class DataFrame(Frame):
    """Frames that carry content (audio, text, etc.)."""
    pass

@dataclass(kw_only=True)
class ControlFrame(Frame):
    """Frames that modify the behavior of processors."""
    pass

@dataclass(kw_only=True)
class UserStartedSpeakingFrame(SystemFrame):
    pass

@dataclass(kw_only=True)
class UserStoppedSpeakingFrame(SystemFrame):
    pass

# --- System Frames ---

@dataclass(kw_only=True)
class StartFrame(SystemFrame):
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(kw_only=True)
class EndFrame(SystemFrame):
    reason: str = "normal"

@dataclass(kw_only=True)
class CancelFrame(SystemFrame):
    reason: str = "cancelled"

@dataclass(kw_only=True)
class ErrorFrame(SystemFrame):
    error: str
    fatal: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

# --- Data Frames ---

@dataclass(kw_only=True)
class AudioFrame(DataFrame):
    data: bytes
    sample_rate: int
    channels: int = 1

@dataclass(kw_only=True)
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

@dataclass(kw_only=True)
class BackpressureFrame(ControlFrame):
    """
     Module 4: Backpressure signal.
    
    Emitted when pipeline queue is full or approaching capacity.
    Processors should drop non-critical frames or pause generation.
    
    Attributes:
        queue_size: Current queue size
        max_size: Maximum queue capacity
        severity: 'warning' (80%% full) or 'critical' (100%% full)
    """
    queue_size: int
    max_size: int
    severity: str = "warning"  # 'warning' or 'critical'

