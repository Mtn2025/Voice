
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app.core.vad.model import SileroOnnxModel


def verify():
    print("🔍 [VERIFY] Checking ONNX Runtime and VAD Model...")

    # 1. Check Path
    model_path = os.path.join(os.getcwd(), "app", "core", "vad", "data", "silero_vad.onnx")
    if not os.path.exists(model_path):
        print(f"❌ Model file MISSING at {model_path}")
        return
    print(f"✅ Model file found at {model_path}")

    # 2. Load Model
    try:
        model = SileroOnnxModel(model_path)
        print("✅ SileroOnnxModel initialized successfully.")

        # 3. Dry Run (Dummy Inference)
        import numpy as np
        dummy_audio = np.zeros(512, dtype=np.float32)
        confidence = model(dummy_audio, 16000)
        print(f"✅ Inference Test (Silence) | Confidence: {confidence:.4f}")

    except Exception as e:
        print(f"❌ Model Load Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
