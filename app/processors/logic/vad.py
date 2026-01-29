import logging
import os
import time
import asyncio
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
    
    ✅ P2: Uses DetectTurnEndUseCase for timer decision (domain ownership)
    """
    def __init__(self, config: Any, detect_turn_end=None, control_channel=None):
        super().__init__(name="VADProcessor")
        self.config = config
        self.control_channel = control_channel # ✅ Module 13: Out-of-Band Signaling
        
        # VAD State
        self.vad_model = None
        self.buffer = bytearray()
        self.speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        
        # ✅ Module 8: Confirmation Window (Gap #12 - False Positive Prevention)
        self._voice_detected_at: float | None = None
        self._confirmation_task: asyncio.Task | None = None
        self._confirmation_cancelled = False
        
        # ✅ P2: DetectTurnEndUseCase (domain ownership of timer logic)
        from app.domain.use_cases import DetectTurnEndUseCase
        self.detect_turn_end = detect_turn_end or DetectTurnEndUseCase(
            silence_threshold_ms=getattr(config, 'silence_timeout_ms', 500)
        )
        logger.info(f"🎯 [VAD] Using DetectTurnEndUseCase (threshold: {self.detect_turn_end.silence_threshold_ms}ms)")
        
        # Smart Turn Parameters
        self.threshold_start = 0.5
        self.threshold_return = 0.35 # Hysteresis
        self.min_speech_frames = 3   # Avoid blips (<100ms)
        
        # Determine Client Type & Config Suffix
        client_type = getattr(self.config, 'client_type', 'twilio')
        self.suffix = ""
        if client_type == "twilio":
            self.suffix = "_phone"
        elif client_type == "telnyx":
            self.suffix = "_telnyx"
            
        def get_conf(base_name, default=None):
            """Helper to get config with profile fallback."""
            val = getattr(self.config, f"{base_name}{self.suffix}", None)
            if val is not None:
                return val
            return getattr(self.config, base_name, default)

        # Barge-in Control (Phase IV)
        self.barge_in_enabled = get_conf('barge_in_enabled', True)
        logger.info(f"🛡️ [VAD] Barge-in: {'ENABLED' if self.barge_in_enabled else 'DISABLED'}")

        # Determine Sample Rate and Timeout based on config (Ritmo/Pacing)
        self.target_sr = 16000 if client_type == 'browser' else 8000
        
        # Determine VAD Threshold
        self.threshold_start = get_conf('interruption_sensitivity', 0.5) # Normalized control 41
        # Fallback to legacy if 0.5 (default)
        if self.threshold_start == 0.5:
             # Try legacy keys
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
        chunk_duration_ms = 32
        chunk_duration_ms = 32
        self.chunk_duration_ms = chunk_duration_ms  # ✅ P2: Store for ms conversion
        val = getattr(self.config, 'silence_timeout_ms', 500)
        timeout_ms = val if val is not None else 500
        self.silence_duration_frames = int(timeout_ms / chunk_duration_ms)
        if self.silence_duration_frames < 1: self.silence_duration_frames = 1
        
        # ✅ Confirmation window (configurable via Settings)
        self.confirmation_window_ms = getattr(self.config, 'vad_confirmation_window_ms', 200)
        self.confirmation_enabled = getattr(self.config, 'vad_enable_confirmation', True)
        
        logger.info(
            f"🎬 [VAD] Confirmation Window: {'ENABLED' if self.confirmation_enabled else 'DISABLED'} "
            f"({self.confirmation_window_ms}ms)"
        )

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
            
            # Simple Frame Energy check for Debugging (Sample every 10th frame to avoid log spam, but user asked for EVERYTHING)
            # Actually, user is angry. Log EVERYTHING for now.
            try:
                # Calculate simple RMS for debug
                import math
                import struct
                # Assume 16-bit PCM
                count = len(chunk_bytes) // 2
                shorts = struct.unpack(f"{count}h", chunk_bytes)
                sum_sq = sum(s*s for s in shorts)
                rms = math.sqrt(sum_sq / count)
                if rms > 100: # Only log if there's some signal
                     logger.debug(f"🎤 [VAD] Frame Energy RMS: {int(rms)} | Buffer: {len(self.buffer)}")
            except:
                pass

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
                
                # ✅ Module 8: Confirmation Window Logic
                if not self.speaking and self.speech_frames >= self.min_speech_frames:
                    if not self._voice_detected_at:
                        # First sustained detection - start confirmation timer
                        self._voice_detected_at = time.time()
                        self._confirmation_cancelled = False
                        
                        if self.confirmation_enabled and self.confirmation_window_ms > 0:
                            # Wait confirmation_window_ms before confirming
                            logger.debug(
                                f"🔍 [VAD] Voice detected - starting {self.confirmation_window_ms}ms "
                                f"confirmation window (Conf: {confidence:.2f})"
                            )
                            self._confirmation_task = asyncio.create_task(
                                self._confirm_voice_detection()
                            )
                        else:
                            # Confirmation disabled - immediate emission (⚠️ legacy behavior)
                            self.speaking = True
                            logger.info(f"🗣️ [VAD] User START speaking (Conf: {confidence:.2f})")
                            await self.push_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)
                            
                            # ✅ Module 13: Barge-In (Out-of-Band Control Signal)
                            if self.control_channel:
                                logger.info(f"⚡ [VAD] Sending OUT-OF-BAND Interrupt Signal (Immediate)")
                                await self.control_channel.send_interrupt(text="VAD Immediate")
                    
                    # Voice still active after detection started
                    elif self._voice_detected_at:
                        elapsed = (time.time() - self._voice_detected_at) * 1000
                        if elapsed >= self.confirmation_window_ms:
                            # ✅ Voice sustained > confirmation window - CONFIRMED
                            if not self.speaking:
                                self.speaking = True
                                    f"✅ [VAD] User START speaking CONFIRMED "
                                    f"(sustained {elapsed:.0f}ms, Conf: {confidence:.2f})"
                                )
                                await self.push_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)
                                
                                # ✅ Module 13: Barge-In (Out-of-Band Control Signal)
                                if self.control_channel:
                                    logger.info(f"⚡ [VAD] Sending OUT-OF-BAND Interrupt Signal")
                                    await self.control_channel.send_interrupt(text="VAD Detected")
                                    
                                self._voice_detected_at = None
                                if self._confirmation_task:
                                    self._confirmation_task.cancel()
                                    self._confirmation_task = None
            
            elif confidence < self.threshold_return:
                # Only count silence if confidence drops below return threshold (Hysteresis)
                self.speech_frames = 0 # Reset speech counter
                
                # ✅ Module 8: Cancel confirmation if voice stops before window expires
                if self._voice_detected_at and not self.speaking:
                    elapsed = (time.time() - self._voice_detected_at) * 1000
                    if elapsed < self.confirmation_window_ms:
                        # ❌ FALSE POSITIVE - Voice stopped before confirmation window
                        logger.warning(
                            f"❌ [VAD] False positive IGNORED - voice lasted only {elapsed:.0f}ms "
                            f"(< {self.confirmation_window_ms}ms threshold)"
                        )
                        self._voice_detected_at = None
                        self._confirmation_cancelled = True
                        if self._confirmation_task:
                            self._confirmation_task.cancel()
                            self._confirmation_task = None
                
                if self.speaking:
                    self.silence_frames += 1
                    
                    # ✅ P2: Delegate timer decision to domain use case
                    silence_ms = self.silence_frames * self.chunk_duration_ms
                    if self.detect_turn_end.should_end_turn(silence_ms):
                        self.speaking = False
                        logger.info(f"🤫 [VAD] User STOP speaking (Silence: {silence_ms}ms)")
                        await self.push_frame(UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    
    async def _confirm_voice_detection(self):
        """
        Confirmation task - waits {confirmation_window_ms} before confirming voice.
        
        If voice stops before window expires, task is cancelled (❌ false positive).
        If voice sustained, UserStartedSpeakingFrame is emitted (✅ confirmed).
        """
        try:
            await asyncio.sleep(self.confirmation_window_ms / 1000.0)
            
            # After confirmation window, check if still detecting voice
            if self._voice_detected_at and not self._confirmation_cancelled:
                elapsed = (time.time() - self._voice_detected_at) * 1000
                logger.info(
                    f"✅ [VAD] Voice CONFIRMED after {elapsed:.0f}ms - "
                    f"emitting UserStartedSpeakingFrame"
                )
                # Note: actual emission happens in main process_frame loop
                # This task just logs confirmation
        
        except asyncio.CancelledError:
            # Task cancelled - means voice stopped before window expired
            logger.debug("[VAD] Confirmation task cancelled (expected for false positives)")

