"""Debug GET endpoint response structure"""
import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

print("="*80)
print("DEBUG: GET /api/config?profile=telnyx Response Structure")
print("="*80)
print()

try:
    response = requests.get(
        f"{BASE_URL}/api/config",
        params={"profile": "telnyx"},
        headers={"X-API-Key": API_KEY},
        timeout=5
    )
    
    if response.status_code == 200:
        data = response.json()
        
        # Check if any of our test values are present
        test_fields = {
            "provider": "groq",
            "model": "llama-3.1-70b-versatile", 
            "temp": 0.85,
            "tokens": 250,
            "prompt": "Eres un asistente de ventas profesional para Telnyx",
            "contextWindow": 12,
            "frequencyPenalty": 0.6
        }
        
        print("Checking for our test values (camelCase aliases):")
        print("-" * 80)
        for key, expected_value in test_fields.items():
            actual_value = data.get(key)
            if actual_value == expected_value:
                print(f"✅ {key}: {actual_value}")
            elif actual_value is not None:
                print(f"⚠️ {key}: {actual_value} (expected: {expected_value})")
            else:
                print(f"❌ {key}: NOT FOUND (expected: {expected_value})")
        
        print()
        print("=" * 80)
        print(f"Total fields returned: {len(data)}")
        print()
        
        # Show sample of what's actually being returned
        print("Sample of actual keys (first 20):")
        print("-" * 80)
        for i, key in enumerate(list(data.keys())[:20]):
            print(f"  {i+1}. {key}: {str(data[key])[:50]}")
            
    else:
        print(f"❌ HTTP {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Exception: {e}")
