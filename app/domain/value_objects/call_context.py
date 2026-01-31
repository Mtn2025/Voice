"""Value Objects for Call Context."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ContactInfo:
    """
    Contact information from CRM (immutable).

    Attributes:
        name: Contact full name
        phone: Phone number
        email: Email address
        company: Company name
        notes: Additional notes about contact

    Example:
        >>> contact = ContactInfo(
        ...     name="Juan Pérez",
        ...     phone="+525551234567",
        ...     company="Acme Corp"
        ... )
        >>> prompt_context = contact.to_prompt_context()
        >>> # "Cliente: Juan Pérez. Empresa: Acme Corp"
    """
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    company: str | None = None
    notes: str | None = None

    def to_prompt_context(self) -> str:
        """
        Format contact info for LLM prompt injection.

        Returns:
            str: Human-readable context string for system prompt

        Example:
            >>> contact = ContactInfo(name="Ana", company="Tech Inc", notes="VIP client")
            >>> context = contact.to_prompt_context()
            >>> # "Cliente: Ana. Empresa: Tech Inc. Notas: VIP client"
        """
        parts = []

        if self.name:
            parts.append(f"Cliente: {self.name}")

        if self.company:
            parts.append(f"Empresa: {self.company}")

        if self.email:
            parts.append(f"Email: {self.email}")

        if self.notes:
            parts.append(f"Notas: {self.notes}")

        return ". ".join(parts) if parts else ""

    @property
    def has_data(self) -> bool:
        """Check if contact has any information."""
        return any([self.name, self.phone, self.email, self.company, self.notes])


@dataclass(frozen=True)
class CallMetadata:
    """
    Call session metadata (immutable).

    Attributes:
        session_id: Unique session identifier (UUID)
        client_type: Client type ("browser", "twilio", "telnyx")
        phone_number: Caller phone number (if applicable)
        started_at: Call start timestamp
        campaign_id: Campaign ID (for outbound calls)

    Example:
        >>> from uuid import uuid4
        >>> metadata = CallMetadata(
        ...     session_id=str(uuid4()),
        ...     client_type="twilio",
        ...     phone_number="+525551234567"
        ... )
        >>> assert metadata.is_inbound
        >>> assert metadata.is_telephony
    """
    session_id: str
    client_type: str  # browser, twilio, telnyx
    phone_number: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    campaign_id: str | None = None

    @property
    def is_inbound(self) -> bool:
        """
        Check if call is inbound (has phone number).

        Returns:
            bool: True if phone_number is present
        """
        return self.phone_number is not None

    @property
    def is_outbound(self) -> bool:
        """
        Check if call is outbound (campaign-based).

        Returns:
            bool: True if campaign_id is present
        """
        return self.campaign_id is not None

    @property
    def is_telephony(self) -> bool:
        """
        Check if call is via telephony provider (not browser).

        Returns:
            bool: True for Twilio/Telnyx
        """
        return self.client_type in ["twilio", "telnyx"]

    @property
    def is_browser(self) -> bool:
        """
        Check if call is via browser simulator.

        Returns:
            bool: True for browser WebSocket
        """
        return self.client_type == "browser"

    @property
    def duration_seconds(self) -> float:
        """
        Calculate call duration so far.

        Returns:
            float: Seconds since call started
        """
        return (datetime.utcnow() - self.started_at).total_seconds()
