"""
Configuration Router - Modular Config Management

Extracted from dashboard.py for clean architecture.
Handles all agent configuration endpoints (browser, twilio, telnyx, core).
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_simple import verify_api_key
from app.db.database import get_db
from app.schemas.config_schemas import (
    BrowserConfigUpdate,
    CoreConfigUpdate,
    TelnyxConfigUpdate,
    TwilioConfigUpdate,
)
from app.services.db_service import db_service
from app.utils.config_utils import update_profile_config

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/config",
    tags=["configuration"],
    dependencies=[Depends(verify_api_key)]
)


@router.patch("/browser")
async def update_browser_config(
    request: Request,
    config: BrowserConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Browser/Simulator profile configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Browser profile configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="browser",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update browser config")
        
        logger.info("✅ Browser config updated successfully")
        return {"status": "ok", "message": "Browser config updated"}
    
    except Exception as e:
        logger.error(f"❌ Browser config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/twilio")
async def update_twilio_config(
    request: Request,
    config: TwilioConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Twilio/Phone profile configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Twilio profile configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="twilio",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update Twilio config")
        
        logger.info("✅ Twilio config updated successfully")
        return {"status": "ok", "message": "Twilio config updated"}
    
    except Exception as e:
        logger.error(f"❌ Twilio config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/telnyx")
async def update_telnyx_config(
    request: Request,
    config: TelnyxConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Telnyx profile configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Telnyx profile configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="telnyx",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update Telnyx config")
        
        logger.info("✅ Telnyx config updated successfully")
        return {"status": "ok", "message": "Telnyx config updated"}
    
    except Exception as e:
        logger.error(f"❌ Telnyx config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/core")
async def update_core_config(
    request: Request,
    config: CoreConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update Core/Global configuration.
    Refactored to use centralized config_utils.
    """
    try:
        logger.info("[CONFIG] Updating Core configuration")
        
        # Use centralized update utility
        updated_config = await update_profile_config(
            db=db,
            profile="core",
            data_dict=config.model_dump(exclude_unset=True)
        )
        
        if not updated_config:
            raise HTTPException(status_code=500, detail="Failed to update core config")
        
        logger.info("✅ Core config updated successfully")
        return {"status": "ok", "message": "Core config updated"}
    
    except Exception as e:
        logger.error(f"❌ Core config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patch")
async def patch_config(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Accepts JSON payload to update specific config fields.
    Example: {"input_min_characters": 30}
    """
    try:
        body = await request.json()
        logger.info(f"[PATCH] Received config patch: {list(body.keys())}")
        
        # Get current config
        config = await db_service.get_agent_config(db)
        
        if not config:
            raise HTTPException(status_code=404, detail="Agent config not found")
        
        # Update config
        config_dict = config.to_dict() if hasattr(config, 'to_dict') else config.__dict__
        config_dict.update(body)
        
        # Save changes
        await db_service.update_agent_config(db, config_dict)
        
        logger.info("✅ Config patched successfully")
        return {"status": "ok", "updated_fields": list(body.keys())}
    
    except Exception as e:
        logger.error(f"❌ Config patch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
