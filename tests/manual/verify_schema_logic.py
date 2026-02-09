
import sys
import os

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.schemas.twilio_schemas import TwilioConfigUpdate
from pydantic import ValidationError

def verify_payload(name, payload, expected_keys):
    print(f"🔍 Testing {name} Payload...")
    try:
        # Create model
        model = TwilioConfigUpdate(**payload)
        dump = model.model_dump(exclude_unset=True, by_alias=False)
        
        # Check keys
        missing = []
        for key in expected_keys:
            if key not in dump:
                missing.append(key)
        
        if missing:
            print(f"❌ FAILED: Missing keys in dump: {missing}")
        else:
            print(f"✅ PASSED: All {len(expected_keys)} keys present.")
            # print(dump)
            
    except ValidationError as e:
        print(f"❌ VALIDATION ERROR: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    print("================================================================================")
    print("   OFFLINE SCHEMA VERIFICATION (Twilio)")
    print("================================================================================")

    # 1. Campaigns (CRM/Webhook) - Was Ignored
    verify_payload("Campaigns", 
        {"crmEnabled": True, "webhookUrl": "http://test.com"}, 
        ["crm_enabled", "webhook_url"]
    )

    # 2. Tools (Tools Schema, Async) - Was Ignored
    verify_payload("Tools",
        {"toolsSchema": {"test": 1}, "asyncTools": True, "toolServerUrl": "http://tools.com"},
        ["tools_schema", "tools_async", "tool_server_url_phone"]
    )

    # 3. System (Limits) - Was Ignored
    verify_payload("System",
        {"concurrencyLimit": 10, "spendLimitDaily": 50.0},
        ["concurrency_limit", "spend_limit_daily"]
    )

    # 4. Standard Twilio
    verify_payload("Model/Voice",
        {"provider": "groq", "voiceId": "juan"},
        ["llm_provider_phone", "voice_name_phone"]
    )

if __name__ == "__main__":
    main()
