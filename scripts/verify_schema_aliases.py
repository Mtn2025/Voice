import os
import sys

sys.path.append(os.getcwd())

from app.schemas.config_schemas import BrowserConfigUpdate


def verify_aliases():
    print("🚀 Verifying Schema Aliases...")

    # Payload simulating store.v2.js (Frontend)
    # Note: store.v2.js uses `temp`, `model`, `msg`, etc.
    frontend_payload = {
        "model": "llama-3-8b",
        "temp": 0.8,
        "prompt": "You are a test bot",
        "msg": "Hello!",
        "mode": "speak-first",
        "voiceId": "en-US-JennyNeural",
        "voiceSpeed": 1.2,
        # Unknown/Extra field
        "ignored_stuff": "should vanish"
    }

    print(f"📦 Input Payload keys: {list(frontend_payload.keys())}")

    try:
        # Parse into Pydantic Model
        config = BrowserConfigUpdate(**frontend_payload)

        # Dump to dict (Backend logic uses this)
        # exclude_unset=True matches config_router logic
        dumped = config.model_dump(exclude_unset=True, by_alias=False)

        print(f"✅ Parsed & Dumped Keys: {list(dumped.keys())}")
        print(f"📄 Dumped Content: {dumped}")

        # Assertions
        assert "llm_model" in dumped
        assert dumped["llm_model"] == "llama-3-8b"
        assert "temperature" in dumped
        assert dumped["temperature"] == 0.8
        assert "system_prompt" in dumped

        assert "ignored_stuff" not in dumped

        print("✅ SUCCESS: Aliases are working correctly!")

    except Exception as e:
        print(f"❌ FAILURE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_aliases()
