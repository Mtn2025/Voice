"""
CRM Manager.

Handles CRM integration, contact context fetching, and status updates.
Adapts internal contact models to LLM context formats.
"""
import datetime
import logging
from typing import Any

from app.db.database import AsyncSessionLocal
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

# Call Status Constants
CALL_STATUS_ENDED = "Call Ended"
CALL_STATUS_VOICEMAIL = "Voicemail"
CALL_STATUS_BUSY = "Busy"
CALL_STATUS_FAILED = "Failed"


class CRMManager:
    """
    Manages CRM contact fetching and status updates.

    Responsibilities:
    - Fetch contact context from CRM (via DB service)
    - Update call status/notes in CRM
    - Format CRM data for LLM system prompt context
    """

    def __init__(self, config: Any, initial_context: dict[str, Any] | None = None):
        """
        Initialize CRM Manager.

        Args:
            config: Agent configuration object
            initial_context: Optional initial context data
        """
        self.config = config
        self.initial_context = initial_context or {}
        self.crm_context: dict[str, Any] = {}

    async def fetch_context(self, phone_number: str | None = None) -> dict[str, Any]:
        """
        Fetch CRM context for contact.

        Args:
            phone_number: Contact phone number

        Returns:
            Dict with CRM contact data
        """
        if not phone_number:
            phone_number = self.initial_context.get("from_number")

        if not phone_number:
            logger.info("📋 [CRM] No phone number available for CRM lookup")
            self.crm_context = {}
            return {}

        logger.debug(f"📋 [CRM] Fetching context for {phone_number}")

        try:
            async with AsyncSessionLocal() as session:
                contact = await db_service.get_contact_by_phone(session, phone_number)

                if contact:
                    self.crm_context = {
                        "name": contact.name,
                        "email": contact.email,
                        "company": contact.company,
                        "notes": contact.notes,
                        "tags": contact.tags or [],
                        "last_interaction": str(contact.updated_at) if contact.updated_at else None
                    }
                    logger.info(f"✅ [CRM] Found contact: {contact.name}")
                else:
                    logger.info(f"[INFO] [CRM] No contact found for {phone_number}")
                    self.crm_context = {}

        except Exception as e:
            logger.error(f"❌ [CRM] Error fetching context: {e}", exc_info=True)
            self.crm_context = {}

        return self.crm_context

    async def update_status(
        self,
        phone_number: str | None = None,
        status: str = CALL_STATUS_ENDED,
        notes: str | None = None
    ):
        """
        Update call information in CRM.

        Updates the 'updated_at' timestamp for the contact.
        Only appends to 'notes' if explicit notes are provided.
        Avoids polluting the database with technical call status logs.

        Args:
            phone_number: Contact phone number
            status: Call status (used for logging, not appended to notes unless implicit)
            notes: Optional meaningful notes to append to contact record
        """
        if not phone_number:
            phone_number = self.initial_context.get("from_number")

        if not phone_number:
            logger.warning("⚠️ [CRM] No phone number for status update")
            return

        logger.info(f"📝 [CRM] Processing update for {phone_number} (Status: {status})")

        try:
            async with AsyncSessionLocal() as session:
                contact = await db_service.get_contact_by_phone(session, phone_number)

                if contact:
                    # Always update interaction timestamp
                    contact.updated_at = datetime.datetime.utcnow()

                    # Only append to notes if there is actual content
                    if notes:
                        existing_notes = contact.notes or ""
                        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        new_note = f"\n[{timestamp_str}] {notes}"
                        contact.notes = existing_notes + new_note
                        logger.info("📝 [CRM] Appended user notes to contact")

                    await session.commit()
                    logger.debug("✅ [CRM] Contact updated successfully")
                else:
                    logger.info("[INFO] [CRM] Contact not found, skipping update")

        except Exception as e:
            logger.error(f"❌ [CRM] Error updating status: {e}", exc_info=True)

    def format_for_prompt(self) -> str:
        """
        Format CRM context for LLM system prompt.

        Returns:
            Formatted string with contact information.
        """
        if not self.crm_context:
            return ""

        parts = []

        if name := self.crm_context.get("name"):
            parts.append(f"Cliente: {name}")

        if company := self.crm_context.get("company"):
            parts.append(f"Empresa: {company}")

        if email := self.crm_context.get("email"):
            parts.append(f"Email: {email}")

        if notes := self.crm_context.get("notes"):
            # Truncate notes to prevent context overflow
            # Now that we don't spam, these notes should be higher quality
            parts.append(f"Notas: {notes[:300]}")

        if tags := self.crm_context.get("tags"):
            parts.append(f"Tags: {', '.join(tags)}")

        return ". ".join(parts)

    def get_context_dict(self) -> dict[str, Any]:
        """Get raw CRM context dictionary."""
        return self.crm_context.copy()
