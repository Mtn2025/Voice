import os
import sys

os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "correct_horse_battery_staple_123" # >12 chars
os.environ["ADMIN_API_KEY"] = "test_key"
os.environ["GROQ_API_KEY"] = "gsk_test"
os.environ["AZURE_SPEECH_KEY"] = "test"
os.environ["AZURE_SPEECH_REGION"] = "eastus"

sys.path.append(os.getcwd())

print("🔍 Verifying Imports...")

try:
    print("1. Importing app.services.base...")
    from app.services.base import STTEvent, STTProvider, STTResultReason
    print("✅ app.services.base OK")

    print("2. Importing app.providers.azure...")
    from app.providers.azure import AzureProvider
    print("✅ app.providers.azure OK")

    print("3. Importing app.processors.logic.stt...")
    from app.processors.logic.stt import STTProcessor
    print("✅ app.processors.logic.stt OK")

    print("4. Importing app.processors.logic.tts...")
    from app.processors.logic.tts import TTSProcessor
    print("✅ app.processors.logic.tts OK")

    print("5. Importing app.core.orchestrator...")
    from app.core.orchestrator import VoiceOrchestrator
    print("✅ app.core.orchestrator OK")

    print("\n🎉 ALL IMPORTS PASSED!")

except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ OTHER ERROR: {e}")
    # print traceback
    import traceback
    traceback.print_exc()
    sys.exit(1)
