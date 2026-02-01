
import asyncio
import os
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

async def verify_voices():
    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    
    print(f"Checking credentials...")
    print(f"Key present: {'Yes' if key else 'No'}")
    print(f"Region: {region}")

    if not key or not region:
        print("❌ MISSING CREDENTIALS")
        return

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    print("Fetching voices from Azure (Blocking)...")
    try:
        # Use run_in_executor to not block main loop, though this script is simple
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: synthesizer.get_voices_async().get())
        
        if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
            print(f"✅ Success! Found {len(result.voices)} voices.")
            
            # Print unique locales
            locales = set(v.locale for v in result.voices)
            print(f"Found {len(locales)} unique languages.")
            print(f"Languages: {sorted(list(locales))[:5]} ...")
        else:
            print(f"❌ Failed. Reason: {result.reason}")
            print(f"Error Details: {result.error_details}")

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(verify_voices())
