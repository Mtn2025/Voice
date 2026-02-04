from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from typing import Annotated
import csv
import io
import logging
from app.core.dialer import Campaign, CampaignDialer

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
logger = logging.getLogger(__name__)

# Single instance for now (or get from app state)
dialer = CampaignDialer() 

@router.post("/start")
async def start_campaign(
    name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    api_key: str  # Simple query auth matching frontend
):
    """
    Start a new outbound campaign from a CSV file.
    Expected CSV columns: phone, name
    """
    # Basic API Key validation (Simplified for this fix)
    # In production use Dependency Injection for security
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    decoded = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(decoded))
    
    leads = []
    for row in csv_reader:
        if 'phone' not in row:
             raise HTTPException(status_code=400, detail="CSV must contain 'phone' column")
        leads.append(row)
        
    if not leads:
        raise HTTPException(status_code=400, detail="CSV is empty")

    logger.info(f"Received campaign '{name}' with {len(leads)} leads")
    
    # Initialize Campaign Object
    campaign = Campaign(id=name.lower().replace(" ", "_"), name=name, data=leads)
    
    # Queue logic (Async)
    await dialer.start_campaign(campaign)
    
    return {
        "status": "queued",
        "campaign_id": campaign.id,
        "leads_count": len(leads),
        "message": f"Campaign '{name}' started successfully with {len(leads)} leads."
    }
