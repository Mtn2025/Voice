import urllib.request
import os

url = 'https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx'
target = 'app/assets/silero_vad.onnx'

print(f"Downloading {url} to {target}...")

req = urllib.request.Request(
    url,
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
)

try:
    with urllib.request.urlopen(req) as response, open(target, 'wb') as out_file:
        data = response.read()
        out_file.write(data)
    print("✅ Download complete.")
except Exception as e:
    print(f"❌ Download failed: {e}")
    exit(1)
