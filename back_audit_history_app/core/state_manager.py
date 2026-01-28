"""
State management for VoiceOrchestrator.
Centralized flags, timeouts, and counters.
"""
import time


class OrchestratorState:
    """
    Centralized state management for VoiceOrchestrator.
    Manages all flags, timeouts, and counters in one place.
    """

    def __init__(self, idle_timeout: float = 10.0, max_duration: int = 600):
        """
        Initialize orchestrator state.

        Args:
            idle_timeout: Seconds before idle message
            max_duration: Maximum call duration in seconds
        """
        # Bot speaking state
        self.is_bot_speaking = False
        self.speech_start_time = None

        # Recognition state
        self.recognition_active = True
        self.final_silence_mode = False

        # Timing
        self.last_activity = time.time()
        self.call_start_time = time.time()
        self.idle_timeout = idle_timeout
        self.max_duration = max_duration

        # Counters
        self.response_id_counter = 0
        self.turn_rms_accumulator = []
        self.interrupted_response_id = None

        # Call control
        self.should_hangup = False
        self.transfer_requested = False
        self.transfer_number = None

    def reset_idle_timer(self):
        """Reset the idle activity timer."""
        self.last_activity = time.time()

    def check_idle_timeout(self) -> bool:
        """
        Check if idle timeout has been exceeded.

        Returns:
            True if timeout exceeded
        """
        return (time.time() - self.last_activity) > self.idle_timeout

    def check_max_duration(self) -> bool:
        """
        Check if maximum call duration has been exceeded.

        Returns:
            True if max duration exceeded
        """
        return (time.time() - self.call_start_time) > self.max_duration

    def update_bot_speaking(self, is_speaking: bool):
        """
        Update bot speaking state.

        Args:
            is_speaking: True if bot is speaking
        """
        self.is_bot_speaking = is_speaking

        if is_speaking:
            self.speech_start_time = time.time()
        else:
            self.speech_start_time = None

    def get_next_response_id(self) -> str:
        """
        Generate next unique response ID.

        Returns:
            Response ID string (e.g., "r_1", "r_2")
        """
        self.response_id_counter += 1
        return f"r_{self.response_id_counter}"

    def add_rms_sample(self, rms: float):
        """
        Add RMS sample to accumulator for turn average.

        Args:
            rms: RMS value to add
        """
        self.turn_rms_accumulator.append(rms)

    def get_turn_average_rms(self) -> float:
        """
        Get average RMS for current turn.

        Returns:
            Average RMS or 0.0 if no samples
        """
        if not self.turn_rms_accumulator:
            return 0.0
        return sum(self.turn_rms_accumulator) / len(self.turn_rms_accumulator)

    def clear_turn_rms(self):
        """Clear RMS accumulator for new turn."""
        self.turn_rms_accumulator = []

    def request_transfer(self, number: str):
        """
        Request call transfer to number.

        Args:
            number: Phone number to transfer to
        """
        self.transfer_requested = True
        self.transfer_number = number

    def request_hangup(self):
        """Request call hangup."""
        self.should_hangup = True
