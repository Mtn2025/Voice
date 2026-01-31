import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.core.frames import AudioFrame, Frame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
from app.core.processor import FrameDirection, FrameProcessor
from app.core.vad.model import SileroOnnxModel
from app.domain.use_cases import DetectTurnEndUseCase

logger = logging.getLogger(__name__)


class VADProcessor(FrameProcessor):
    """
    Analyzes AudioFrames using Silero VAD (ONNX) to detect Voice Activity.
    Emits UserStartedSpeakingFrame / UserStoppedSpeakingFrame based on 'Smart Turn' logic.
    """
    def __init__(self, config: Any, detect_turn_end=None, control_channel=None):
        super().__init__(name="VADProcessor")
        self.config = config
        self.control_channel = control_channel

        # VAD State
        self.vad_model = None
        self.buffer = bytearray()
        self.speaking = False
        self.silence_frames = 0
        self.speech_frames = 0

        # State: Confirmation Window (False Positive Prevention)
        self._voice_detected_at: float | None = None

        # Domain Logic: Turn End Detection
        self.detect_turn_end = detect_turn_end or DetectTurnEndUseCase(
            silence_threshold_ms=getattr(config, 'silence_timeout_ms', 500)
        )
        logger.debug(f"🎯 [VAD] Using DetectTurnEndUseCase (threshold: {self.detect_turn_end.silence_threshold_ms}ms)")

        # Smart Turn Parameters
        self.threshold_start = 0.5
        self.threshold_return = 0.35 # Hysteresis
        self.min_speech_frames = 3   # Avoid blips (<100ms)

        # Get profile configuration (type-safe, centralized)
        client_type = getattr(self.config, 'client_type', 'twilio')
        profile = self.config.get_profile(client_type)

        # Barge-in Control
        self.barge_in_enabled = profile.barge_in_enabled if profile.barge_in_enabled is not None else True

        # Determine Sample Rate
        self.target_sr = 16000 if client_type == 'browser' else 8000

        # Determine VAD Threshold (with fallback priority)
        self.threshold_start = profile.interruption_sensitivity or profile.vad_threshold or 0.5

        logger.info(f"🎤 [VAD] Init | Client: {client_type} | SR: {self.target_sr} | Sensitivity: {self.threshold_start}")

        # Calculate Chunk Duration (Silero requirement)
        # 512 samples @ 16k = 32ms. 256 samples @ 8k = 32ms.
        self.chunk_duration_ms = 32

        # Confirmation window
        self.confirmation_window_ms = getattr(self.config, 'vad_confirmation_window_ms', 200)
        self.confirmation_enabled = getattr(self.config, 'vad_enable_confirmation', True)

        # Initialize Model
        self._init_model()

    def _init_model(self):
        """Locate and load Silero ONNX model."""
        try:
            # Try standard relative path first
            model_path = Path("app/core/vad/data/silero_vad.onnx")

            # If strictly checking relative to CWD
            if not model_path.exists():
                 # Try absolute construct
                 model_path = Path.cwd() / "app" / "core" / "vad" / "data" / "silero_vad.onnx"

            if model_path.exists():
                self.vad_model = SileroOnnxModel(str(model_path))
            else:
                 logger.warning(f"⚠️ Silero ONNX model not found at {model_path}. VAD disabled.")

        except Exception as e:
            logger.error(f"Could not init SileroVAD: {e}. VAD will be disabled.")

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                await self._process_audio(frame)
                await self.push_frame(frame, direction) # Pass audio through
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
        required_samples = 512 if self.target_sr == 16000 else 256
        chunk_size = required_samples * 2

        while len(self.buffer) >= chunk_size:
            chunk_bytes = self.buffer[:chunk_size]
            self.buffer = self.buffer[chunk_size:]

            # Convert bytes to float32 numpy array
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

                # Logic: Start Speaking?
                if not self.speaking and self.speech_frames >= self.min_speech_frames:

                    if not self._voice_detected_at:
                        # First detection: Mark timestamp
                        self._voice_detected_at = time.time()

                        if not self.confirmation_enabled or self.confirmation_window_ms <= 0:
                            # Immediate trigger (No confirmation)
                            await self._trigger_start_speaking(confidence, immediate=True)

                    elif self._voice_detected_at:
                        # Sustained detection: Check confirmation window
                        elapsed_ms = (time.time() - self._voice_detected_at) * 1000
                        if elapsed_ms >= self.confirmation_window_ms:
                            # Confirmed! trigger
                            await self._trigger_start_speaking(confidence, immediate=False, elapsed=elapsed_ms)

            elif confidence < self.threshold_return:
                # Logic: Stop Speaking?

                # Check for False Positive (Voice stopped before confirmation)
                if self._voice_detected_at and not self.speaking:
                    elapsed_ms = (time.time() - self._voice_detected_at) * 1000
                    if elapsed_ms < self.confirmation_window_ms:
                        # False positive, reset
                        self._voice_detected_at = None
                        self.speech_frames = 0
                        # We do NOT log every false positive to avoid noise, unless debug

                if self.speaking:
                    self.silence_frames += 1

                    # Check Turn End
                    silence_ms = self.silence_frames * self.chunk_duration_ms
                    if self.detect_turn_end.should_end_turn(silence_ms):
                        self.speaking = False
                        logger.info(f"🤫 [VAD] User STOP speaking (Silence: {silence_ms}ms)")
                        await self.push_frame(UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)

    async def _trigger_start_speaking(self, confidence: float, immediate: bool, elapsed: float = 0):
        """Helper to emit start speaking events."""
        self.speaking = True
        self._voice_detected_at = None

        msg_type = "Immediate" if immediate else f"Confirmed ({int(elapsed)}ms)"
        logger.info(f"🗣️ [VAD] User START speaking [{msg_type}] (Conf: {confidence:.2f})")

        await self.push_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)

        # Barge-In (Out-of-Band)
        if self.control_channel:
            logger.debug("⚡ [VAD] Sending OUT-OF-BAND Interrupt Signal")
            await self.control_channel.send_interrupt(text="VAD Voice Detected")
