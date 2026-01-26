import logging
from typing import Any

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, RMSFrame, AudioFrame, ControlFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
# from app.core.vad_filter import AdaptiveInputFilter # Legacy
from app.core.vad.analyzer import SileroVADAnalyzer

logger = logging.getLogger(__name__)

class VADProcessor(FrameProcessor):
    """
    Analyzes AudioFrames using Silero VAD to detect Voice Activity.
    Emits UserStartedSpeakingFrame / UserStoppedSpeakingFrame.
    Also filters TextFrames based on VAD state (optional).
    """
    def __init__(self, config: Any):
        super().__init__(name="VADProcessor")
        self.config = config
        
        # VAD State
        self.vad_analyzer = None
        self.buffer = bytearray()
        self.speaking = False
        self.silence_frames = 0
        
        # Configurable Parameters
        self.threshold = 0.5
        # Determine Sample Rate and Timeout based on config (Ritmo/Pacing)
        client_type = getattr(self.config, 'client_type', 'twilio')
        target_sr = 16000 if client_type == 'browser' else 8000
        
        # Calculate Frames for Timeout (Chunk duration is ~32ms for Silero standard chunks)
        # 512 samples @ 16k = 32ms. 256 samples @ 8k = 32ms.
        chunk_duration_ms = 32
        timeout_ms = getattr(self.config, 'silence_timeout_ms', 500)
        self.silence_duration_frames = int(timeout_ms / chunk_duration_ms)
        if self.silence_duration_frames < 1: self.silence_duration_frames = 1

        try:
            self.vad_analyzer = SileroVADAnalyzer(sample_rate=target_sr)
        except Exception as e:
            logger.error(f"Could not init SileroVAD: {e}. VAD will be disabled.")

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AudioFrame):
                await self._process_audio(frame)
                await self.push_frame(frame, direction) # Pass audio through
                
            elif isinstance(frame, TextFrame):
                # We could filter text if we are sure user wasn't speaking
                # For now, let's pass it, or use legacy RMS logic here if needed.
                # Ideally, VAD frames downstream (Aggregator) handle the logic.
                await self.push_frame(frame, direction)
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _process_audio(self, frame: AudioFrame):
        if not self.vad_analyzer:
            return

        # 1. Add to buffer
        self.buffer.extend(frame.data)
        
        # 2. Process in correct chunk sizes
        chunk_size = self.vad_analyzer.num_frames_required() * 2 # 2 bytes per sample (int16)
        
        while len(self.buffer) >= chunk_size:
            chunk = self.buffer[:chunk_size]
            self.buffer = self.buffer[chunk_size:]
            
            confidence = self.vad_analyzer.process(bytes(chunk))
            
            if confidence > self.threshold:
                self.silence_frames = 0
                if not self.speaking:
                    self.speaking = True
                    logger.info(f"🗣️ [VAD] User START speaking (Conf: {confidence:.2f})")
                    await self.push_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)
            else:
                if self.speaking:
                    self.silence_frames += 1
                    if self.silence_frames > self.silence_duration_frames:
                        self.speaking = False
                        logger.info(f"🤫 [VAD] User STOP speaking (Silence)")
                        await self.push_frame(UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)

