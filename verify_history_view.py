
import asyncio
import logging
import json
import os
from unittest.mock import AsyncMock
import httpx
from sqlalchemy import text
from app.db.database import engine, AsyncSessionLocal
from app.db.models import Base
from app.routers.history_router import get_call_detail

# Mock Router request dependency
from fastapi import HTTPException
from app.db.models import Call, Transcript

async def manual_test_history_view():
    print("🚀 Verifying History View Logic...")
    
    # 1. Setup DB Data (using existing dev.db or test)
    # This test assumes the previous validation script populated the DB.
    # We will try to fetch the LAST call.
    
    async with AsyncSessionLocal() as session:
        # Get Max ID
        res = await session.execute(text("SELECT MAX(id) FROM calls"))
        last_id = res.scalar()
        
        if not last_id:
            print("❌ No calls found in DB. Run validation script first.")
            return

        print(f"🔍 Fetching details for Call ID: {last_id}")
        
        # 2. Call the Endpoint Function Directly (Bypass HTTP for speed/simplicity)
        try:
            response = await get_call_detail(call_id=last_id, db=session)
            
            # 3. Validate Response Structure
            # { "call": {...}, "transcripts": [...] }
            
            call = response["call"]
            transcripts = response["transcripts"]
            
            print(f"📄 Call Data: ID={call['id']}, Client={call['client_type']}")
            
            if call["extracted_data"]:
                 print("✅ Extracted Data Present")
                 if isinstance(call["extracted_data"], str):
                     print(f"   JSON String: {call['extracted_data'][:50]}...")
                 else:
                     print(f"   JSON Object: {json.dumps(call['extracted_data'])[:50]}...")
            else:
                 print("⚠️ Extracted Data Missing (Might be expected if test failed previously)")
            
            print(f"📝 Transcripts Count: {len(transcripts)}")
            for t in transcripts:
                print(f"   [{t['role'].upper()}] {t['content']}")

            # 4. Final Assertions
            if len(transcripts) > 0 and call["id"] == last_id:
                print("✅ PASSED: History Endpoint works correctly.")
            else:
                print("❌ FAILED: Data mismatch or empty.")

        except HTTPException as e:
            print(f"❌ HTTP Error: {e.detail}")
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(manual_test_history_view())
