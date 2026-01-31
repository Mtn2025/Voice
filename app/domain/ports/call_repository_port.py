"""
CallRepositoryPort - Domain Port for Call Management.

Abstraction over call history database operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CallRecord:
    """
    Call Record Value Object (Domain).

    Immutable representation of a call session.
    """
    id: int
    stream_id: str
    client_type: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    status: str = "active"  # active, completed, failed


class CallRepositoryPort(ABC):
    """
    Port for call record management.

    Abstraction over database (SQLAlchemy, MongoDB, etc.)
    """

    @abstractmethod
    async def create_call(
        self,
        stream_id: str,
        client_type: str,
        metadata: dict
    ) -> CallRecord:
        """
        Create new call record.

        Args:
            stream_id: Unique stream identifier
            client_type: Client type (browser, twilio, telnyx)
            metadata: Additional metadata

        Returns:
            CallRecord with assigned ID
        """
        pass

    @abstractmethod
    async def end_call(self, call_id: int) -> None:
        """
        Finalize call record.

        Args:
            call_id: Call record ID to finalize
        """
        pass

    @abstractmethod
    async def get_call(self, call_id: int) -> CallRecord | None:
        """
        Get call record by ID.

        Args:
            call_id: Call record ID

        Returns:
            CallRecord or None if not found
        """
        pass
