import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ADMIN_API_KEY", "secret123")
BASE_URL = "http://localhost:8000"

# Test with explicit debugging
test_cases = [
    ("contextWindow", 25),
    ("toolChoice", "required"),
    ("voicePitch", -5),
    ("temp", 0.8),
]

for key, value in test_cases:
    payload = {key: value}
    r = requests.post(
        f"{BASE_URL}/api/config/update-json",
        json=payload,
        headers={"X-API-Key": API_KEY}
    )
    result = r.json()
    status = "✅" if result.get("updated", 0) > 0 else "❌"
    print(f"{status} {key:20} → updated={result.get('updated', 0)}, normalized={result.get('normalized', 0)}")
