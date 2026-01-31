"""
Barge-In Use Case - Domain Logic.

Handles user interruption during bot speech, coordinating
state cleanup and interruption signals.
"""
import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class BargeInCommand:
    """Command returned by Use Case for orchestrator to execute."""
    clear_pipeline: bool = True
    interrupt_audio: bool = True
    reason: str = ""


class AudioManagerProtocol(Protocol):
    """Protocol for audio manager dependency."""
    async def interrupt_speaking(self) -> None:
        """Interrupt current audio playback."""
        ...


class PipelineProtocol(Protocol):
    """Protocol for pipeline dependency."""
    async def clear_output_queue(self) -> None:
        """Clear pending output frames."""
        ...


class HandleBargeInUseCase:
    """
    Domain Use Case: Handle user interruption (barge-in).

    Pure domain logic - NO infrastructure dependencies.
    Returns command for orchestrator to execute.
    """

    def execute(self, reason: str) -> BargeInCommand:
        """
        Process barge-in event.

        Args:
            reason: Interruption reason (e.g., "user_spoke", "vad_detected")

        Returns:
            BargeInCommand with actions to perform
        """
        logger.info(f"[Barge-In Use Case] Triggered: {reason}")

        # Domain logic: determine what to clean up based on reason
        if "vad" in reason.lower() or "user" in reason.lower():
            # User speech detected - full interruption
            return BargeInCommand(
                clear_pipeline=True,
                interrupt_audio=True,
                reason=reason
            )
        # Other reasons - conservative interruption
        return BargeInCommand(
            clear_pipeline=False,
            interrupt_audio=True,
            reason=reason
        )
