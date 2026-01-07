"""
Voice Activity Detection (VAD) Filter with adaptive calibration.
"""


class AdaptiveInputFilter:
    """
    Self-calibrating VAD filter.
    Learns user's RMS profile to distinguish Voice vs Noise.
    """

    def __init__(self):
        self.samples = 0
        self.avg_rms = 0.0
        self.min_rms = 1.0  # Floor
        self.max_rms = 0.0
        self.ready = False

    def update_profile(self, rms: float):
        """Update RMS profile with new sample."""
        self.samples += 1

        # Running average
        self.avg_rms = (self.avg_rms * (self.samples - 1) + rms) / self.samples

        # Track min/max
        self.min_rms = min(rms, self.min_rms)
        self.max_rms = max(rms, self.max_rms)

        # Ready after 5+ samples
        if self.samples >= 5:
            self.ready = True

    def should_filter(self, text: str, current_turn_rms: float, min_chars: int = 4):
        """
        Determines if recognized text should be filtered as noise.

        Args:
            text: Recognized text from STT
            current_turn_rms: Average RMS of this turn
            min_chars: Minimum characters to consider valid

        Returns:
            (should_filter, reason)
        """
        # Check 1: Text length
        if len(text) < min_chars:
            return (True, "Too short")

        # Check 2: RMS profile (if calibrated)
        if self.ready and current_turn_rms > 0:
            # Threshold: 40% of average
            threshold = self.avg_rms * 0.4

            if current_turn_rms < threshold:
                return (True, f"Low RMS ({current_turn_rms:.3f} < {threshold:.3f})")

        # Default: Don't filter
        return (False, "Valid")
