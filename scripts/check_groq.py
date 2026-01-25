import asyncio
import os
import sys
from dotenv import load_dotenv

# Load .env explicitly before importing settings
load_dotenv(".env")

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.providers.groq import GroqProvider

async def main():
    print(f"Checking Groq API Key...")
    if not settings.GROQ_API_KEY:
        print("❌ ERROR: GROQ_API_KEY is missing/empty in settings!")
        print(f"Env var GROQ_API_KEY: {os.environ.get('GROQ_API_KEY')}")
        # Allow proceeding to see the error message if we force it? No, provider needs key.
        return

    # Mask key for safety
    masked = settings.GROQ_API_KEY[:4] + "..." + settings.GROQ_API_KEY[-4:]
    print(f"Key present: {masked}")
    
    provider = GroqProvider()
    print("Initializing provider...")
    
    try:
        print("Attempting simple generation...")
        stream = provider.get_stream(
            messages=[{"role": "user", "content": "Say hello"}],
            system_prompt="You are a test bot.",
            temperature=0.7,
            max_tokens=50
        )
        
        print("Stream created. Reading chunks...")
        full_response = ""
        async for chunk in stream:
            full_response += chunk
            print(f"Chunk received: {chunk}")
            
        print(f"✅ Success! Response: {full_response}")
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
