
import asyncio
import os
from app.adapters.outbound.tts.azure_tts_adapter import AzureTTSAdapter
from app.core.config import settings

async def main():
    print("🚀 Initializing Azure Adapter...")
    adapter = AzureTTSAdapter()
    
    print("☁️ Fetching voices...")
    # Force a fetch
    voices = await adapter.get_available_voices()
    
    target_voice = "es-MX-BeatrizNeural"
    found = False
    
    for v in voices:
        if v.id == target_voice:
            found = True
            print(f"✅ Found {target_voice}")
            
            # Check internal cache for raw styles
            # accessing private struct for debug
            from app.adapters.outbound.tts.azure_tts_adapter import _STYLE_CACHE
            
            styles = _STYLE_CACHE.get(target_voice, [])
            print(f"🎨 Styles in Cache for {target_voice}: {styles}")
            
            # Also check if there were any raw styles from API if possible?
            # The adapter transforms them immediately.
            # But the styles printed above are what the frontend receives.
            
            if not styles:
                print("👍 Styles list is EMPTY correctly.")
            else:
                print("❌ Styles list is NOT EMPTY. This causes the UI to show.")
                for s in styles:
                    print(f"   - {s}")
            break
            
    if not found:
        print(f"❌ Voice {target_voice} not found in Azure list!")

if __name__ == "__main__":
    asyncio.run(main())
