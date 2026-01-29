
import asyncio
import logging
from typing import List, Dict, Optional
import uuid

# Assuming we have a service to initiate calls. 
# We need to reuse TelnyxService logic or creating a new outbound trigger.
# Usually this involves sending a POST to Telnyx API or our own /call endpoint?
# Better: Use our internal logic. The system flow for outbound is: 
# 1. Trigger Telnyx Call Control (Method 'dial').
# 2. When call answers, Telnyx webhook hits our /webhook/telnyx endpoint.
# 3. We need to associate that Call Leg ID with the Campaign Context.

logger = logging.getLogger(__name__)

class Campaign:
    def __init__(self, name: str, data: List[Dict]):
        self.id = str(uuid.uuid4())
        self.name = name
        self.data = data # List of dicts: [{'phone': '+123', 'name': 'John'}, ...]
        self.status = "pending"
        self.results = []

class CampaignDialer:
    """
    Manages outbound calling campaigns (Bolna-Style).
    """
    def __init__(self):
        self._active_campaigns: Dict[str, Campaign] = {}
        self._running = False
        self._task = None
        self._queue = asyncio.Queue()

    async def start_campaign(self, campaign: Campaign):
        """Queue all numbers from a campaign."""
        self._active_campaigns[campaign.id] = campaign
        logger.info(f"🚀 Starting Campaign: {campaign.name} ({len(campaign.data)} leads)")
        
        for lead in campaign.data:
            await self._queue.put((campaign.id, lead))
            
        if not self._running:
            self.start_worker()

    def start_worker(self):
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self):
        logger.info("📞 Dialer Worker Started")
        
        from app.db.database import AsyncSessionLocal
        from app.services.db_service import db_service
        
        while self._running:
            try:
                # 1. Fetch Config (Dynamic Pacing & Credentials)
                config_overrides = {}
                pacing = 2.0
                
                try:
                    async with AsyncSessionLocal() as session:
                        conf = await db_service.get_agent_config(session)
                        if conf:
                            # Pacing Calculation
                            rate_limit = getattr(conf, 'rate_limit_telnyx', 30) or 30
                            pacing = 60.0 / float(rate_limit)
                            
                            # Credentials for Dialing
                            config_overrides = {
                                "api_key": getattr(conf, 'telnyx_api_key', None),
                                "from_number": getattr(conf, 'caller_id_telnyx', None) or getattr(conf, 'telnyx_from_number', None),
                                "connection_id": getattr(conf, 'telnyx_connection_id', None)
                            }
                except Exception as e:
                    logger.warning(f"Dialer access Config DB failed: {e}")

                # 2. Process Queue
                campaign_id, lead = await self._queue.get()
                
                phone = lead.get('phone')
                if phone:
                    await self._dial_lead(campaign_id, lead, config_overrides)
                
                self._queue.task_done()
                
                # Dynamic Pacing Wait
                await asyncio.sleep(pacing)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dialer Error: {e}")
                await asyncio.sleep(1.0) # Prevent tight loop on error

    async def _dial_lead(self, campaign_id: str, lead: Dict, config: Dict):
        """
        Initiates the outbound call via Telnyx API using provided config.
        """
        from app.services.telephony import telnyx_client
        
        phone = lead.get('phone')
        if not phone: return

        # Construct Context
        context = {
            "campaign_id": campaign_id,
            "lead_data": lead
        }
        
        logger.info(f"☎️ Dialing {phone} for Campaign {campaign_id}")
        await telnyx_client.dial(phone, context, config)

dialer_service = CampaignDialer()
