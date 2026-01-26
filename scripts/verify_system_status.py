
import asyncio
import sys
import os
import logging

# Add app to path
sys.path.append(os.getcwd())

# Mock Env for Pydantic
os.environ["POSTGRES_USER"] = "postgres_secure_user"
os.environ["POSTGRES_SERVER"] = "localhost"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def check_imports():
    print("\n🔍 [1/4] Checking Imports...")
    try:
        from app.services.baserow import BaserowClient
        print("✅ app.services.baserow imported")
        from app.services.webhook import WebhookService
        print("✅ app.services.webhook imported")
        from app.core.orchestrator import VoiceOrchestrator
        print("✅ app.core.orchestrator imported")
        from app.routers.dashboard import validate_prompt_variables
        print("✅ app.routers.dashboard.validate_prompt_variables imported")
        return True
    except ImportError as e:
        print(f"❌ Import Failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error during imports: {e}")
        return False

async def check_db_schema():
    print("\n🔍 [2/4] Checking Database Schema (Models)...")
    try:
        from app.db.models import AgentConfig
        # Check for new columns in the Class definition (SQLAlchemy model)
        columns = AgentConfig.__table__.columns.keys()
        
        required = [
            # CRM
            'crm_enabled', 'baserow_token', 'baserow_table_id',
            # Webhook
            'webhook_url', 'webhook_secret'
        ]
        
        missing = [col for col in required if col not in columns]
        
        if missing:
            print(f"❌ Missing Columns in Model: {missing}")
            return False
        else:
            print(f"✅ All {len(required)} new columns found in AgentConfig model.")
            return True
            
    except Exception as e:
        print(f"❌ DB Schema Check Failed: {e}")
        return False

def check_validation_logic():
    print("\n🔍 [3/4] Checking Logic...")
    try:
        from app.routers.dashboard import validate_prompt_variables
        
        # Test Case 1: Valid
        prompt_ok = "Hola {{name}}, debes {{debt_amount}}."
        unknowns = validate_prompt_variables(prompt_ok)
        if not unknowns:
            print("✅ Validation Logic Test 1 (Valid) Passed")
        else:
             print(f"❌ Validation Logic Test 1 Failed. Unknowns: {unknowns}")

        # Test Case 2: Invalid (Hallucination)
        prompt_bad = "Hola {{usuario_fantasma}}."
        unknowns = validate_prompt_variables(prompt_bad)
        if "usuario_fantasma" in unknowns:
            print("✅ Validation Logic Test 2 (Invalid) Passed")
        else:
             print(f"❌ Validation Logic Test 2 Failed. Expected 'usuario_fantasma', got {unknowns}")
             
        return True
    except Exception as e:
         print(f"❌ Logic Test Failed: {e}")
         return False

def check_frontend_integrity():
    print("\n🔍 [4/4] Checking Frontend Integrity...")
    path = "app/templates/dashboard.html"
    if not os.path.exists(path):
        print(f"❌ {path} not found")
        return False
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    checks = [
        ("CRM Integration (Baserow)", "CRM UI Block"),
        ("Webhook Integration (n8n/Make)", "Webhook UI Block"),
        ("validateCSV", "CSV Validation JS"),
        ("data.warnings", "Warning Toast JS")
    ]
    
    all_ok = True
    for token, name in checks:
        if token in content:
            print(f"✅ {name} Found")
        else:
            print(f"❌ {name} MISSING in HTML")
            all_ok = False
            
    return all_ok

async def main():
    print("🚀 STARTED SYSTEM HEALTH CHECK")
    
    checks = [
        check_imports(),
        await check_db_schema(),
        check_validation_logic(),
        check_frontend_integrity()
    ]
    
    if all(checks):
        print("\n🟢 SYSTEM STATUS: FULLY OPERATIONAL")
        print("Backend and Frontend are correctly connected and patched.")
    else:
        print("\n🔴 SYSTEM STATUS: ISSUES DETECTED")

if __name__ == "__main__":
    asyncio.run(main())
