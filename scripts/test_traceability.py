import os
import sys
import unittest
from unittest.mock import MagicMock

# Set SECURE dummy env vars to satisfy Pydantic
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_password_secure"
os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_HOST"] = "localhost"

sys.path.append(".")

from app.core.orchestrator import VoiceOrchestrator
from app.db.models import AgentConfig


class TestTraceability(unittest.TestCase):
    def test_overlay_logic_tools(self):
        print("\n🧪 TESTING ORCHESTRATOR TRACEABILITY (OVERLAYS)")
        print("============================================")

        # 1. Setup Config with Separation
        config = AgentConfig()

        # Base (Browser)
        config.tool_server_url = "https://n8n.base.com"

        # Phone (Twilio)
        config.tool_server_url_phone = "https://n8n.phone.com"

        # Telnyx
        config.tool_server_url_telnyx = "https://n8n.telnyx.com"

        # 2. Test Twilio Identity
        orch_phone = VoiceOrchestrator(transport=MagicMock(), client_type="twilio")
        orch_phone.config = config

        # Apply Overlay
        orch_phone._apply_profile_overlay()

        print(f"   [Twilio] Expected: https://n8n.phone.com | Actual: {orch_phone.config.tool_server_url}")
        self.assertEqual(orch_phone.config.tool_server_url, "https://n8n.phone.com")

        # 3. Test Telnyx Identity
        orch_telnyx = VoiceOrchestrator(transport=MagicMock(), client_type="telnyx")
        orch_telnyx.config = config # Reset needed if config was mutated?
        # CAUTION: Models are mutable. _apply_profile_overlay mutates the object.
        # We should use a fresh object or reset.
        config.tool_server_url = "https://n8n.base.com"

        orch_telnyx.config = config
        orch_telnyx._apply_profile_overlay()

        print(f"   [Telnyx] Expected: https://n8n.telnyx.com | Actual: {orch_telnyx.config.tool_server_url}")
        self.assertEqual(orch_telnyx.config.tool_server_url, "https://n8n.telnyx.com")

        print("✅ PASSED: Overlay logic respects profile separation.")

if __name__ == '__main__':
    unittest.main()
