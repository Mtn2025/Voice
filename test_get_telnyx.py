"""Test GET /api/config?profile=telnyx"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

print("="*80)
print("Testing GET /api/config?profile=telnyx")
print("="*80)
print()

try:
    response = requests.get(
        f"{BASE_URL}/api/config",
        params={"profile": "telnyx"},
        headers={"X-API-Key": API_KEY},
        timeout=5
    )
    
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - Retrieved {len(data)} fields")
        print()
        print("First 10 fields:")
        for i, (key, value) in enumerate(list(data.items())[:10]):
            print(f"  {key}: {value}")
    else:
        print(f"❌ FAIL - {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
