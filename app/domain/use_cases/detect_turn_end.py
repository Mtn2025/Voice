"""
DetectTurnEndUseCase.

Moves timer logic from processor to domain layer (hexagonal architecture).
"""
import logging

logger = logging.getLogger(__name__)


class DetectTurnEndUseCase:
    """
    Domain use case for detecting when user turn should end.

    Hexagonal Architecture: Timer logic belongs in domain, NOT processor.

    Example:
        >>> use_case = DetectTurnEndUseCase(silence_threshold_ms=500)
        >>>
        >>> # In VADProcessor
        >>> if use_case.should_end_turn(silence_duration_ms):
        ...     await self.push_frame(EndOfSpeechFrame())
    """

    def __init__(self, silence_threshold_ms: int = 500):
        """
        Initialize turn end detection.

        Args:
            silence_threshold_ms: Milliseconds of silence before ending turn
        """
        self.silence_threshold_ms = silence_threshold_ms
        logger.info(f"[DetectTurnEnd] Initialized with {silence_threshold_ms}ms threshold")

    def should_end_turn(self, silence_duration_ms: int) -> bool:
        """
        Determine if user turn should end based on silence duration.

        Args:
            silence_duration_ms: Current silence duration in milliseconds

        Returns:
            True if turn should end, False otherwise
        """
        should_end = silence_duration_ms >= self.silence_threshold_ms

        if should_end:
            logger.debug(
                f"[DetectTurnEnd] Turn ending - Silence: {silence_duration_ms}ms "
                f">= Threshold: {self.silence_threshold_ms}ms"
            )

        return should_end

    def update_threshold(self, new_threshold_ms: int):
        """
        Update silence threshold dynamically.

        Args:
            new_threshold_ms: New threshold in milliseconds
        """
        old_threshold = self.silence_threshold_ms
        self.silence_threshold_ms = new_threshold_ms

        logger.info(
            f"[DetectTurnEnd] Threshold updated: {old_threshold}ms → {new_threshold_ms}ms"
        )
