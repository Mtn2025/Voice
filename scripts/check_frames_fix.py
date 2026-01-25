import sys
import os

# Add project root
sys.path.append(os.getcwd())

print("Attempting to import app.core.frames...")
try:
    from app.core.frames import Frame, ErrorFrame, AudioFrame, TextFrame, EndFrame
    print("✅ Import successful. Class definitions are valid.")
    
    print("Testing instantiation...")
    
    # Test 1: ErrorFrame (The one that broke)
    # Must use Keyword Args now
    e = ErrorFrame(error="Test Error")
    print(f"✅ ErrorFrame instantiated: {e}")
    
    # Test 2: AudioFrame
    a = AudioFrame(data=b'123', sample_rate=8000)
    print(f"✅ AudioFrame instantiated: {a}")
    
    # Test 3: EndFrame (Defaults)
    end = EndFrame()
    print(f"✅ EndFrame instantiated: {end}")
    
except TypeError as te:
    print(f"❌ TYPE ERROR (Likely the Field Order issue): {te}")
    exit(1)
except Exception as e:
    print(f"❌ OTHER ERROR: {e}")
    exit(1)
