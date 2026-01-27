from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List
import csv
import io
# Import dialer_service from core.dialer. 
# Note: Ensure imports avoid circular dependencies if necessary, but this should be fine.
from app.core.dialer import dialer_service, Campaign
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/start")
async def start_campaign(
    name: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Starts a new outbound calling campaign from a CSV file.
    CSV headers must include: 'phone' and 'name'.
    """
    try:
        content = await file.read()
        text = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))
        
        leads = []
        for row in reader:
            # Normalize keys to lowercase
            normalized_row = {k.lower().strip(): v for k, v in row.items()}
            
            # Check for phone key variations
            phone = normalized_row.get('phone') or normalized_row.get('telefono') or normalized_row.get('tel')
            
            if phone:
                # Ensure phone is saved in standard key 'phone'
                normalized_row['phone'] = phone
                leads.append(normalized_row)
                
        if not leads:
            raise HTTPException(status_code=400, detail="CSV must contain 'phone' column and data")
            
        campaign = Campaign(name=name, data=leads)
        await dialer_service.start_campaign(campaign)
        
        return {
            "status": "started",
            "campaign_id": campaign.id,
            "leads_count": len(leads)
        }
        
    except Exception as e:
        logger.error(f"Error starting campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))
