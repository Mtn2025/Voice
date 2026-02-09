import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

print(f"Using API Key: {API_KEY[:20]}...")

# Test contextWindow
payload1 = {"contextWindow": 25}
print(f"\n1. Testing contextWindow = 25")
r1 = requests.post(
    f"{BASE_URL}/api/config/update-json",
    json=payload1,
    headers={"X-API-Key": API_KEY}
)
print(f"Status: {r1.status_code}")
print(f"Response: {r1.json()}")

# Test toolChoice
payload2 = {"toolChoice": "required"}
print(f"\n2. Testing toolChoice = 'required'")
r2 = requests.post(
    f"{BASE_URL}/api/config/update-json",
    json=payload2,
    headers={"X-API-Key": API_KEY}
)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.json()}")

# Test voicePitch (should work)
payload3 = {"voicePitch": -5}
print(f"\n3. Testing voicePitch = -5 (control)")
r3 = requests.post(
    f"{BASE_URL}/api/config/update-json",
    json=payload3,
    headers={"X-API-Key": API_KEY}
)
print(f"Status: {r3.status_code}")
print(f"Response: {r3.json()}")
