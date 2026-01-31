
import json
import logging
import os

import aiohttp

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

    async def dial(self, to_number: str, context_data: dict, config: dict | None = None):
        """
        Initiates an outbound call.
        'context_data' is encoded into 'client_state' string (base64).
        'config': Optional dictionary with keys: api_key, from_number, connection_id
        """
        import base64

        # Resolve Credentials (Priority: Config arg > Env Var)
        config = config or {}
        api_key = config.get("api_key") or TELNYX_API_KEY
        from_number = config.get("from_number") or TELNYX_FROM_NUMBER
        connection_id = config.get("connection_id") or os.getenv("TELNYX_CONNECTION_ID")

        if not api_key or not from_number or not connection_id:
            logger.error("❌ Telnyx Config Missing (API Key, From Number or Connection ID)")
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Serialize context
        json_str = json.dumps(context_data)
        client_state_b64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

        payload = {
            "connection_id": connection_id,
            "to": to_number,
            "from": from_number,
            "client_state": client_state_b64
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}/calls", headers=headers, json=payload) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        call_id = data['data']['call_control_id']
                        logger.info(f"✅ Outbound Call Initiated: {call_id} -> {to_number}")
                        return call_id
                    text = await resp.text()
                    logger.error(f"❌ Telnyx Call Failed ({resp.status}): {text}")
                    return None
            except Exception as e:
                logger.error(f"Telephony Error: {e}")
                return None

telnyx_client = TelnyxClient()
