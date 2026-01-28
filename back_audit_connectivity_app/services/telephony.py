
import os
import aiohttp
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
TELNYX_FROM_NUMBER = os.getenv("TELNYX_FROM_NUMBER", "+15550000000")
# The URL that Telnyx should call back when call is answered (Inbound XML or Webhook)
# For outbound voice agent, we usually point to a TeXML bin or our own /webhook/answer
TELNYX_WEBHOOK_URL = os.getenv("TELNYX_WEBHOOK_URL", "https://api.tu-dominio.com/webhook/telnyx")

class TelnyxClient:
    """
    Client for Telnyx REST API (Outbound Calling).
    """
    def __init__(self):
        self.base_url = "https://api.telnyx.com/v2"
        self.headers = {
            "Authorization": f"Bearer {TELNYX_API_KEY}",
            "Content-Type": "application/json"
        }

    async def dial(self, to_number: str, context_data: Dict):
        """
        Initiates an outbound call.
        'context_data' is encoded into 'client_state' string (base64) so we can retrieve it 
        in the webhook when the user answers.
        """
        import base64
        
        # Serialize context
        json_str = json.dumps(context_data)
        client_state_b64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        
        payload = {
            "connection_id": os.getenv("TELNYX_CONNECTION_ID"), # Required for Call Control
            "to": to_number,
            "from": TELNYX_FROM_NUMBER,
            "client_state": client_state_b64, 
            # When answered, where to send the webhook?
            # Standard Telnyx App sends webhooks to the configured URL in Portal.
            # But we can override or standard behavior applies.
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}/calls", headers=self.headers, json=payload) as resp:
                    if resp.status == 200 or resp.status == 201:
                        data = await resp.json()
                        call_id = data['data']['call_control_id']
                        logger.info(f"✅ Outbound Call Initiated: {call_id} -> {to_number}")
                        return call_id
                    else:
                        text = await resp.text()
                        logger.error(f"❌ Telnyx Call Failed ({resp.status}): {text}")
                        return None
            except Exception as e:
                logger.error(f"Telephony Error: {e}")
                return None

telnyx_client = TelnyxClient()
