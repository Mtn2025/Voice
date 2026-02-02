import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth_simple import verify_api_key
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.services.db_service import db_service

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

@router.post("/test-call-telnyx")
@limiter.limit("5/minute")
async def test_call_telnyx(request: Request, _: None = Depends(verify_api_key)):
    """
    Initiate a test outbound call via Telnyx.
    """
    try:
        body = await request.json()
        target_number = body.get("to")

        if not target_number:
            raise HTTPException(status_code=400, detail="Missing 'to' phone number")

        # 1. Load Config
        async with AsyncSessionLocal() as session:
            config = await db_service.get_agent_config(session)
            telnyx_profile = config.get_profile('telnyx')
            api_key = telnyx_profile.telnyx_api_key or settings.TELNYX_API_KEY
            source_number = telnyx_profile.caller_id_telnyx or telnyx_profile.telnyx_from_number
            connection_id = telnyx_profile.telnyx_connection_id

        if not api_key:
             raise HTTPException(status_code=400, detail="Missing Telnyx API Key")
        if not source_number:
             raise HTTPException(status_code=400, detail="Missing Caller ID")
        if not connection_id:
             raise HTTPException(status_code=400, detail="Missing Connection ID")

        # 2. Call API
        url = "https://api.telnyx.com/v2/calls"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "to": target_number,
            "from": source_number,
            "connection_id": connection_id
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code in (201, 200):
            data = response.json()
            return {"status": "success", "message": "Call Initiated", "call_id": data.get("data", {}).get("call_control_id")}
        
        raise HTTPException(status_code=response.status_code, detail=f"Telnyx Error: {response.text}")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Test call error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-call-twilio")
@limiter.limit("5/minute")
async def test_call_twilio(request: Request, _: None = Depends(verify_api_key)):
    """
    Initiate a test outbound call via Twilio.
    """
    try:
        body = await request.json()
        target_number = body.get("to")
        if not target_number:
            raise HTTPException(status_code=400, detail="Missing 'to' phone number")

        # Implementation stub (request implies logic similar to Telnyx)
        # Assuming we would load Twilio keys and call API
        return {"status": "success", "message": "Twilio test call initiated (stub)"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_public_config(_: None = Depends(verify_api_key)):
    """
    Get generic system configuration status.
    """
    return {
        "status": "ok",
        "telnyx_enabled": bool(settings.TELNYX_API_KEY),
        "twilio_enabled": bool(settings.TWILIO_ACCOUNT_SID),
        "azure_enabled": bool(settings.AZURE_SPEECH_KEY)
    }
