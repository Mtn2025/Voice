"""
Control Channel.

A dedicated mechanism for out-of-band signaling that bypasses the main data pipeline.
This architecture prevents Head-of-Line (HOL) blocking, ensuring that critical control
signals (like interruptions or emergency stops) are processed immediately, regardless
of the depth of the data queue.
"""
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ControlSignal(str, Enum):
    """High-priority control signals."""
    INTERRUPT = "interrupt"          # User barge-in detected
    CANCEL = "cancel"                # Cancel current operation
    PAUSE = "pause"                  # Pause audio output
    RESUME = "resume"                # Resume audio output
    EMERGENCY_STOP = "emergency_stop"  # Immediate shutdown
    CLEAR_PIPELINE = "clear_pipeline"  # Clear all queued frames


@dataclass
class ControlMessage:
    """
    Control message payload.

    Attributes:
        signal: Type of control signal
        metadata: Additional context (e.g., user text causing interrupt)
    """
    signal: ControlSignal
    metadata: dict[str, Any]


class ControlChannel:
    """
    Dedicated channel for control signals.

    Runs independently from data pipeline to ensure immediate response.
    Uses asyncio.Event for non-blocking signal delivery.

    Design:
        - Control signals bypass PriorityQueue (preventing HOL blocking)
        - Event-driven architecture (wait_for_signal blocks until signal arrives)
        - Thread-safe with asyncio.Lock

    Usage:
        # Producer (e.g., VAD processor)
        await control_channel.send(ControlSignal.INTERRUPT, {'text': 'user spoke'})

        # Consumer (e.g., orchestrator control loop)
        while active:
            msg = await control_channel.wait_for_signal()
            handle_control_message(msg)
    """

    def __init__(self):
        """Initialize control channel."""
        self._event = asyncio.Event()
        self._message: ControlMessage | None = None
        self._lock = asyncio.Lock()
        self._stats = {
            'signals_sent': 0,
            'signals_received': 0
        }

    async def send(self, signal: ControlSignal, metadata: dict[str, Any] | None = None) -> None:
        """
        Send control signal (non-blocking).

        Args:
            signal: Type of control signal
            metadata: Optional context (e.g., text, reason)

        Note:
            If previous signal not yet consumed, it will be overwritten.
            This is intentional - latest signal takes priority.
        """
        async with self._lock:
            self._message = ControlMessage(
                signal=signal,
                metadata=metadata or {}
            )
            self._stats['signals_sent'] += 1
            self._event.set()

            logger.debug(
                f"[ControlChannel] Signal sent: {signal.value} "
                f"(metadata: {metadata or {}})"
            )

    async def wait_for_signal(self, timeout: float | None = None) -> ControlMessage | None:
        """
        Wait for next control signal.

        Args:
            timeout: Optional timeout in seconds (None = wait forever)

        Returns:
            ControlMessage when signal is received.

        Raises:
            asyncio.TimeoutError: If timeout specified and exceeded
        """
        try:
            # Wait for signal with optional timeout
            if timeout:
                await asyncio.wait_for(self._event.wait(), timeout=timeout)
            else:
                await self._event.wait()

            # Retrieve and clear message
            async with self._lock:
                msg = self._message
                self._message = None
                self._event.clear()
                self._stats['signals_received'] += 1

                if msg:
                    logger.debug(
                        f"[ControlChannel] Signal received: {msg.signal.value}"
                    )

                return msg

        except TimeoutError:
            # logger.debug("[ControlChannel] wait_for_signal timeout")
            raise

    def has_pending(self) -> bool:
        """
        Check if signal is pending (non-blocking).

        Returns:
            True if signal waiting to be consumed
        """
        return self._event.is_set()

    async def clear(self) -> None:
        """
        Clear any pending signal.

        Useful for cleanup or reset scenarios.
        """
        async with self._lock:
            self._message = None
            self._event.clear()
            logger.debug("[ControlChannel] Cleared pending signals")

    def get_stats(self) -> dict[str, int]:
        """
        Get channel statistics.

        Returns:
            Dictionary with signals_sent, signals_received
        """
        return self._stats.copy()

    async def send_interrupt(self, text: str = "") -> None:
        """
        Convenience method: Send INTERRUPT signal.

        Args:
            text: Optional user text causing interrupt
        """
        await self.send(
            ControlSignal.INTERRUPT,
            {'text': text, 'reason': 'user_barge_in'}
        )

    async def send_cancel(self, reason: str = "") -> None:
        """
        Convenience method: Send CANCEL signal.

        Args:
            reason: Why cancellation requested
        """
        await self.send(
            ControlSignal.CANCEL,
            {'reason': reason}
        )

    async def send_emergency_stop(self, reason: str = "") -> None:
        """
        Convenience method: Send EMERGENCY_STOP signal.

        Args:
            reason: Why emergency stop triggered
        """
        await self.send(
            ControlSignal.EMERGENCY_STOP,
            {'reason': reason}
        )
