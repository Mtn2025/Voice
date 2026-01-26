
import os

source = 'dashboard_monolith.html'
dest = 'dashboard_monolith_utf8.html'

if not os.path.exists(source):
    print(f"Error: {source} not found")
    exit(1)

content = None
# Try UTF-16 (PowerShell default)
try:
    with open(source, 'r', encoding='utf-16') as f:
        content = f.read()
    print("Read as UTF-16")
except Exception as e:
    print(f"UTF-16 failed: {e}")

# Try UTF-8 (Git default)
if content is None:
    try:
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
        print("Read as UTF-8")
    except Exception as e:
        print(f"UTF-8 failed: {e}")

# Try System Default (CP1252/MBCS)
if content is None:
    try:
        with open(source, 'r', encoding='mbcs') as f:
            content = f.read()
        print("Read as MBCS")
    except Exception as e:
        print(f"MBCS failed: {e}")

if content:
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Success: Wrote {dest}")
else:
    print("Failed to read file in any encoding")
