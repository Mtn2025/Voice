
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import csv
import io
import logging
from app.core.dialer import dialer_service, Campaign

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/start")
async def start_campaign(name: str, file: UploadFile = File(...)):
    """
    Upload a CSV file (headers: phone, name, ...) to start an outbound campaign.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        content = await file.read()
        decoded = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        
        leads = []
        for row in reader:
            # Normalize keys if needed
            if 'phone' not in row:
                # Try to find a column looking like phone?
                # For now strict.
                continue
            leads.append(row)
            
        if not leads:
             raise HTTPException(status_code=400, detail="No valid rows found (header 'phone' required)")

        campaign = Campaign(name=name, data=leads)
        
        # Start in background
        await dialer_service.start_campaign(campaign)
        
        return {"status": "started", "campaign_id": campaign.id, "leads_count": len(leads)}

    except Exception as e:
        logger.error(f"Campaign Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
