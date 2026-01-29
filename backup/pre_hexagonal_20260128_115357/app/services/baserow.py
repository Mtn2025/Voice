
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class BaserowClient:
    """
    Async Client for Baserow API.
    Used to fetch context and update interaction history.
    """
    def __init__(self, token: str, base_url: str = "https://api.baserow.io"):
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

    async def find_contact(self, table_id: int, phone: str) -> Optional[Dict[str, Any]]:
        """
        Search for a row containing the phone number.
        Returns the first match or None.
        """
        if not phone or not table_id:
            return None

        url = f"{self.base_url}/api/database/rows/table/{table_id}/"
        params = {
            "search": phone,
            "size": 1
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self.headers, params=params, timeout=5.0)
                
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get('results', [])
                    if results:
                        logger.info(f"✅ [BASEROW] Contact found: {phone} -> Row ID: {results[0]['id']}")
                        return results[0]
                    else:
                        logger.info(f"ℹ️ [BASEROW] Contact not found: {phone}")
                        return None
                else:
                    logger.error(f"❌ [BASEROW] Search Error {resp.status_code}: {resp.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ [BASEROW] Connection Error: {e}")
            return None

    async def update_contact(self, table_id: int, row_id: int, data: Dict[str, Any]) -> bool:
        """
        Update a specific row with new data (e.g. Status, Notes).
        """
        if not row_id or not table_id:
            return False

        url = f"{self.base_url}/api/database/rows/table/{table_id}/{row_id}/"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.patch(url, headers=self.headers, json=data, timeout=5.0)
                
                if resp.status_code == 200:
                    logger.info(f"✅ [BASEROW] Row {row_id} updated successfully.")
                    return True
                else:
                    logger.error(f"❌ [BASEROW] Update Error {resp.status_code}: {resp.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ [BASEROW] Connection Error (Update): {e}")
            return False
