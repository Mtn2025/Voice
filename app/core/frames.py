import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(kw_only=True)
class Frame:
    """
    Base class for all frames in the pipeline.

    Attributes:
        id (str): Unique identifier for the frame instance.
        name (str): Class name of the frame.
        timestamp (float): Creation time (Unix timestamp).
        trace_id (str): Distributed tracing ID (Conversational turn ID).
        span_id (str): Span ID for this specific frame processing unit.
        metadata (Dict[str, Any]): Arbitrary metadata.
    """
    id: str = field(init=False)
    name: str = field(init=False)
    timestamp: float = field(default_factory=time.time)

    # Distributed Tracing Support
    trace_id: str = field(default="")
    span_id: str = field(init=False)

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.id = str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.name = self.__class__.__name__

        # Generate trace_id if not provided
        if not self.trace_id:
            self.trace_id = str(uuid.uuid4())

    def to_dict(self, include_binary: bool = False) -> dict[str, Any]:
        """
        Convert frame to dictionary.

        Args:
            include_binary: If False, truncates/omits large binary fields for logging/JSON safety.
        """
        data = asdict(self)

        # Helper to clean non-serializable data
        if not include_binary and 'data' in data and isinstance(data['data'], bytes):
            data['data'] = f"<bytes len={len(data['data'])}>"

        return data

    def __str__(self):
        return f"<{self.name} id={self.id[:8]}>"

@dataclass(kw_only=True)
class SystemFrame(Frame):
    """Frames that have high priority (Level 1) and control the pipeline flow."""
    pass

@dataclass(kw_only=True)
class DataFrame(Frame):
    """Frames that carry content (audio, text, etc.) with normal priority (Level 2)."""
    pass

@dataclass(kw_only=True)
class ControlFrame(Frame):
    """Frames that modify the behavior of processors with normal priority (Level 2)."""
    pass

# --- System Frames (High Priority) ---

@dataclass(kw_only=True)
class StartFrame(SystemFrame):
    """Signal to start processing or a new interaction."""
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(kw_only=True)
class EndFrame(SystemFrame):
    """Signal to end processing or interaction."""
    reason: str = "normal"

@dataclass(kw_only=True)
class CancelFrame(SystemFrame):
    """Signal to cancel current operation immediately."""
    reason: str = "cancelled"

@dataclass(kw_only=True)
class EndTaskFrame(SystemFrame):
    """Signal to end a specific task/tool execution."""
    task_id: str = ""
    result: dict[str, Any] = field(default_factory=dict)

@dataclass(kw_only=True)
class ErrorFrame(SystemFrame):
    """Signal that an error has occurred."""
    error: str
    fatal: bool = False
    context: dict[str, Any] = field(default_factory=dict)

@dataclass(kw_only=True)
class UserStartedSpeakingFrame(SystemFrame):
    """Signal detected by VAD that user has started speaking."""
    pass

@dataclass(kw_only=True)
class UserStoppedSpeakingFrame(SystemFrame):
    """Signal detected by VAD that user has stopped speaking."""
    pass

@dataclass(kw_only=True)
class BackpressureFrame(SystemFrame):
    """
    Backpressure signal emitted when pipeline queue is full or approaching capacity.

    Classified as SystemFrame to ensure High Priority (Level 1) handling,
    preventing the signal itself from being blocked by the congestion it reports.

    Attributes:
        queue_size: Current queue size
        max_size: Maximum queue capacity
        severity: 'warning' (80% full) or 'critical' (100% full)
    """
    queue_size: int
    max_size: int
    severity: str = "warning"  # 'warning' or 'critical'

# --- Data Frames (Normal Priority) ---

@dataclass(kw_only=True)
class AudioFrame(DataFrame):
    """Frame containing raw audio data."""
    data: bytes
    sample_rate: int
    channels: int = 1

@dataclass(kw_only=True)
class TextFrame(DataFrame):
    """Frame containing text data (transcript or response)."""
    text: str
    is_final: bool = True

@dataclass(kw_only=True)
class ImageFrame(DataFrame):
    """Frame containing image data."""
    data: bytes
    format: str
    size: tuple[int, int]

@dataclass(kw_only=True)
class RMSFrame(DataFrame):
    """Frame containing Root Mean Square audio levels (for visualization)."""
    rms: float

# --- Control Frames (Normal Priority) ---

@dataclass(kw_only=True)
class UpdateSettingsFrame(ControlFrame):
    """Frame to update processor settings dynamically."""
    settings: dict[str, Any]
