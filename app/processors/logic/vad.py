import logging
import os
from typing import Any

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, RMSFrame, AudioFrame, ControlFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
# from app.core.vad_filter import AdaptiveInputFilter # Legacy
from app.core.vad.model import SileroOnnxModel

logger = logging.getLogger(__name__)

class VADProcessor(FrameProcessor):
    """
    Analyzes AudioFrames using Silero VAD (ONNX) to detect Voice Activity.
    Emits UserStartedSpeakingFrame / UserStoppedSpeakingFrame based on 'Smart Turn' logic.
    """
    def __init__(self, config: Any):
        super().__init__(name="VADProcessor")
        self.config = config
        
        # VAD State
        self.vad_model = None
        self.buffer = bytearray()
        self.speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        
        # Smart Turn Parameters
        self.threshold_start = 0.5
        self.threshold_return = 0.35 # Hysteresis
        self.min_speech_frames = 3   # Avoid blips (<100ms)
        
        # Determine Sample Rate and Timeout based on config (Ritmo/Pacing)
        client_type = getattr(self.config, 'client_type', 'twilio')
        self.target_sr = 16000 if client_type == 'browser' else 8000
        
        # Determine VAD Threshold
        # Default 0.5 if not found
        if client_type == 'browser':
            self.threshold_start = getattr(self.config, 'vad_threshold', 0.5)
        elif client_type == 'telnyx':
            self.threshold_start = getattr(self.config, 'vad_threshold_telnyx', 0.5)
        else:
            self.threshold_start = getattr(self.config, 'vad_threshold_phone', 0.5)
            
        logger.info(f"🎤 [VAD] Init | Client: {client_type} | SR: {self.target_sr} | Threshold: {self.threshold_start}")
        
        # Calculate Frames for Timeout (Chunk duration is ~32ms for Silero standard chunks)
        # 512 samples @ 16k = 32ms. 256 samples @ 8k = 32ms.
        chunk_duration_ms = 32
        timeout_ms = getattr(self.config, 'silence_timeout_ms', 500)
        self.silence_duration_frames = int(timeout_ms / chunk_duration_ms)
        if self.silence_duration_frames < 1: self.silence_duration_frames = 1

        try:
            # Locate Model File
            # Assuming 'app/core/vad/data/silero_vad.onnx' or relative path
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # app/processors/logic -> app/processors -> app
            # Actually __file__ is app/processors/logic/vad.py
            # We need app/core/vad/data/silero_vad.onnx
            # Go up 3 levels? app/processors/logic -> app/processors -> app -> root?
            # Better: use relative import logic or hardcoded for now based on known structure
            # Root is usually CWD in main.py
            model_path = "app/core/vad/data/silero_vad.onnx"
            if not os.path.exists(model_path):
                 # Try absolute if CWD is wrong
                 model_path = os.path.join(os.getcwd(), "app", "core", "vad", "data", "silero_vad.onnx")
            
            if os.path.exists(model_path):
                self.vad_model = SileroOnnxModel(model_path)
            else:
                 # If model missing, we can try to download or warn
                 # For now, warn
                 logger.warning(f"⚠️ Silero ONNX model not found at {model_path}. VAD disabled.")
                 
        except Exception as e:
            logger.error(f"Could not init SileroVAD: {e}. VAD will be disabled.")

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                await self._process_audio(frame)
                await self.push_frame(frame, direction) # Pass audio through
                
            elif isinstance(frame, TextFrame):
                await self.push_frame(frame, direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _process_audio(self, frame: AudioFrame):
        if not self.vad_model:
            return

        # 1. Add to buffer
        self.buffer.extend(frame.data)
        
        # 2. Process in correct chunk sizes (Silero Requirement)
        # 256 samples (8k) or 512 samples (16k) * 2 bytes = 512 or 1024 bytes
        required_samples = 512 if self.target_sr == 16000 else 256
        chunk_size = required_samples * 2 
        
        while len(self.buffer) >= chunk_size:
            chunk_bytes = self.buffer[:chunk_size]
            self.buffer = self.buffer[chunk_size:]
            
            # Convert bytes to float32 numpy array
            # int16 -> float32 normalized
            import numpy as np
            audio_int16 = np.frombuffer(chunk_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            try:
                confidence = self.vad_model(audio_float32, self.target_sr)
            except Exception as e:
                logger.error(f"VAD Inference Error: {e}")
                confidence = 0.0
            
            # Smart Turn Logic
            if confidence > self.threshold_start:
                self.silence_frames = 0
                self.speech_frames += 1
                
                # Only trigger start if sustained speech (blip avoidance)
                if not self.speaking and self.speech_frames >= self.min_speech_frames:
                    self.speaking = True
                    logger.info(f"🗣️ [VAD] User START speaking (Conf: {confidence:.2f})")
                    await self.push_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)
            
            elif confidence < self.threshold_return:
                # Only count silence if confidence drops below return threshold (Hysteresis)
                self.speech_frames = 0 # Reset speech counter
                if self.speaking:
                    self.silence_frames += 1
                    if self.silence_frames > self.silence_duration_frames:
                        self.speaking = False
                        logger.info(f"🤫 [VAD] User STOP speaking (Silence)")
                        await self.push_frame(UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)

