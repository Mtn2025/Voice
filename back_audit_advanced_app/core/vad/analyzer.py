
import time
import numpy as np
import logging
from typing import Optional
from pathlib import Path

from app.core.vad.model import SileroOnnxModel

logger = logging.getLogger(__name__)

class SileroVADAnalyzer:
    """
    Analyzes audio chunks to detect voice activity using Silero VAD.
    """
    def __init__(self, sample_rate: int = 8000):
        self.sample_rate = sample_rate
        self._model = None
        self._last_reset_time = 0
        self._reset_interval = 5.0 # Seconds
        
        # Load model using absolute path
        # Assuming model is in app/assets/silero_vad.onnx
        try:
            # Locate asset relative to project root or this file
            # Current file: app/core/vad/analyzer.py
            # Asset: app/assets/silero_vad.onnx
            base_dir = Path(__file__).parent.parent.parent.parent
            model_path = base_dir / "app" / "assets" / "silero_vad.onnx"
            
            if not model_path.exists():
                logger.error(f"Silero VAD model not found at {model_path}")
                raise FileNotFoundError(f"Model not found: {model_path}")
                
            self._model = SileroOnnxModel(str(model_path))
            logger.info("Silero VAD initialized successfully.")
            
        except Exception as e:
            logger.error(f"Failed to initialize Silero VAD: {e}")
            raise

    def set_sample_rate(self, sample_rate: int):
        if sample_rate not in [8000, 16000]:
             raise ValueError("Silero VAD supports only 8000 or 16000 Hz")
        self.sample_rate = sample_rate

    def num_frames_required(self) -> int:
        return 512 if self.sample_rate == 16000 else 256

    def process(self, buffer: bytes) -> float:
        """
        Process audio buffer and return voice confidence (0.0 - 1.0).
        Buffer must be 16-bit PCM.
        """
        if not self._model:
            return 0.0

        try:
            # Convert bytes to int16 then float32 normalized
            audio_int16 = np.frombuffer(buffer, np.int16)
            
            # Check length matches requirement
            required = self.num_frames_required()
            if len(audio_int16) != required:
                # If buffer is wrong size, we can't process this chunk directly with Silero
                # Caller should ensure chunking.
                # Silent failure or log?
                # logger.debug(f"VAD Buffer size mismatch: {len(audio_int16)} vs {required}")
                return 0.0

            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Run inference
            # Output is [[confidence]]
            output = self._model(audio_float32, self.sample_rate)
            confidence = output[0][0]

            # Periodic reset
            curr_time = time.time()
            if curr_time - self._last_reset_time > self._reset_interval:
                self._model.reset_states()
                self._last_reset_time = curr_time

            return float(confidence)

        except Exception as e:
            logger.error(f"VAD Processing Error: {e}")
            return 0.0
