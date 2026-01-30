import asyncio
import httpx
import json
import os

# Assuming running inside container on port 8000
BASE_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")
API_KEY = os.getenv("ADMIN_API_KEY", "") 

async def simulate_save():
    print(f"🚀 Simulating 'Save Config' button click...")
    print(f"📡 Target: {BASE_URL}/config/browser")

    # Payload matching the UI structure
    payload = {
        "llm_provider": "groq",
        "llm_model": "llama-3.3-70b-versatile",
        "temperature": 0.5,
        "max_tokens": 300,
        "first_message": "Hola, esto es una prueba de guardado simulado.",
        "system_prompt": "Eres un asistente de prueba.",
        "voice_settings": {
            "rate": 1.0,
            "pitch": 0
        }
    }

    headers = {
        "Content-Type": "application/json"
    }
    
    # Add API Key if needed (mostly for external calls, but checking just in case)
    params = {}
    if API_KEY:
        params["api_key"] = API_KEY

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{BASE_URL}/config/browser", 
                json=payload,
                params=params,
                timeout=10.0
            )
            
            print(f"📥 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Configuration Saved Successfully!")
                print("📝 Response Data:", json.dumps(data, indent=2))
                return True
            else:
                print("❌ Save Failed!")
                print("🔴 Error:", response.text)
                return False

        except Exception as e:
            print(f"💥 Connection Error: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(simulate_save())
