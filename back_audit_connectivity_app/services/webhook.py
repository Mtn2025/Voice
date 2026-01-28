
import logging
import httpx
import time
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WebhookService:
    """
    Handles external system integration via Webhooks.
    Implements the "End-of-Call Report" pattern (Vapi Style).
    """
    def __init__(self, url: str, secret: Optional[str] = None):
        self.url = url
        self.secret = secret
        self.headers = {"Content-Type": "application/json"}
        if self.secret:
            self.headers["X-Webhook-Secret"] = self.secret

    async def send_end_call_report(self, 
                                   call_id: str, 
                                   agent_config_name: str,
                                   metadata: Dict[str, Any],
                                   transcript: list,
                                   analysis: Optional[Dict[str, Any]] = None,
                                   recording_url: Optional[str] = None) -> bool:
        """
        Sends the standard JSON payload to the configured webhook.
        """
        if not self.url:
            return False

        payload = {
            "event": "call.ended",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "call_id": call_id,
            "agent_id": agent_config_name,
            "metadata": metadata, # Passes through Baserow ID, Campaign ID, etc.
            "analysis": analysis or {"success": False, "summary": "No analysis performed."},
            "transcript": transcript,
            "recording_url": recording_url
        }

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"📡 [WEBHOOK] Sending End-of-Call Report to {self.url}...")
                resp = await client.post(self.url, json=payload, headers=self.headers, timeout=10.0)
                
                if resp.status_code in [200, 201, 202, 204]:
                    logger.info(f"✅ [WEBHOOK] delivered successfully ({resp.status_code}).")
                    return True
                else:
                    logger.warning(f"⚠️ [WEBHOOK] Delivery failed: {resp.status_code} - {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"❌ [WEBHOOK] Connection Error: {e}")
            return False
