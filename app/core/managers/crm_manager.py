"""CRM Manager - Handles CRM integration and contact management."""
import logging
from typing import Optional, Dict, Any
from app.services.db_service import db_service
from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class CRMManager:
    """
    Manages CRM contact fetching and status updates.
    
    Responsibilities:
    - Fetch contact context from CRM
    - Update call status in CRM
    - Format CRM data for LLM context
    
    Extracted from VoiceOrchestrator for separation of concerns.
    """
    
    def __init__(self, config, initial_context: Dict[str, Any] = None):
        """
        Initialize CRM Manager.
        
        Args:
            config: Agent configuration
            initial_context: Optional initial context data (from Telnyx/Twilio)
        """
        self.config = config
        self.initial_context = initial_context or {}
        self.crm_context: Dict[str, Any] = {}
    
    async def fetch_context(self, phone_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch CRM context for contact.
        
        Args:
            phone_number: Contact phone number
        
        Returns:
            Dict with CRM contact data
        """
        # Try phone number from initial context if not provided
        if not phone_number:
            phone_number = self.initial_context.get("from_number")
        
        if not phone_number:
            logger.info("📋 [CRM] No phone number available for CRM lookup")
            return {}
        
        logger.info(f"📋 [CRM] Fetching context for {phone_number}")
        
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
                    logger.info(f"ℹ️ [CRM] No contact found for {phone_number}")
                    self.crm_context = {}
        
        except Exception as e:
            logger.error(f"❌ [CRM] Error fetching context: {e}", exc_info=True)
            self.crm_context = {}
        
        return self.crm_context
    
    async def update_status(
        self, 
        phone_number: Optional[str] = None,
        status: str = "Call Ended",
        notes: Optional[str] = None
    ):
        """
        Update call status in CRM.
        
        Args:
            phone_number: Contact phone number
            status: Call status (e.g., "Call Ended", "Voicemail", "Busy")
            notes: Optional notes to append
        """
        if not phone_number:
            phone_number = self.initial_context.get("from_number")
        
        if not phone_number:
            logger.warning("⚠️ [CRM] No phone number for status update")
            return
        
        logger.info(f"📝 [CRM] Updating status for {phone_number}: {status}")
        
        try:
            async with AsyncSessionLocal() as session:
                contact = await db_service.get_contact_by_phone(session, phone_number)
                
                if contact:
                    # Update contact notes with call status
                    existing_notes = contact.notes or ""
                    timestamp = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_note = f"\n[{timestamp}] {status}"
                    
                    if notes:
                        new_note += f": {notes}"
                    
                    contact.notes = existing_notes + new_note
                    
                    await session.commit()
                    logger.info(f"✅ [CRM] Updated contact status")
                else:
                    logger.info(f"ℹ️ [CRM] Contact not found, skipping status update")
        
        except Exception as e:
            logger.error(f"❌ [CRM] Error updating status: {e}", exc_info=True)
    
    def format_for_prompt(self) -> str:
        """
        Format CRM context for LLM system prompt.
        
        Returns:
            Formatted string with contact information
        """
        if not self.crm_context:
            return ""
        
        parts = []
        
        if self.crm_context.get("name"):
            parts.append(f"Cliente: {self.crm_context['name']}")
        
        if self.crm_context.get("company"):
            parts.append(f"Empresa: {self.crm_context['company']}")
        
        if self.crm_context.get("email"):
            parts.append(f"Email: {self.crm_context['email']}")
        
        if self.crm_context.get("notes"):
            parts.append(f"Notas: {self.crm_context['notes'][:200]}")  # Truncate long notes
        
        if self.crm_context.get("tags"):
            tags_str = ", ".join(self.crm_context["tags"])
            parts.append(f"Tags: {tags_str}")
        
        return ". ".join(parts) if parts else ""
    
    def get_context_dict(self) -> Dict[str, Any]:
        """Get raw CRM context dictionary."""
        return self.crm_context.copy()
