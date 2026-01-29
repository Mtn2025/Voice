"""
Unit tests for VAD Confirmation Window - Module 8.

Validates confirmation window logic to prevent false positive interruptions.
Tests scenarios: confirmed voice, false positives, disabled confirmation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from app.processors.logic.vad import VADProcessor
from app.core.frames import AudioFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
from app.core.processor import FrameDirection


class MockConfig:
    """Mock configuration for VAD testing."""
    def __init__(
        self,
        vad_confirmation_window_ms=200,
        vad_enable_confirmation=True,
        client_type='twilio',
        vad_threshold_phone=0.5,
        silence_timeout_ms=500
    ):
        self.vad_confirmation_window_ms = vad_confirmation_window_ms
        self.vad_enable_confirmation = vad_enable_confirmation
        self.client_type = client_type
        self.vad_threshold_phone = vad_threshold_phone
        self.silence_timeout_ms = silence_timeout_ms


class TestVADConfirmationWindow:
    """Test suite for VAD confirmation window (Gap #12 resolution)."""
    
    @pytest.mark.asyncio
    async def test_voice_confirmed_after_200ms(self):
        """Voice sustained > 200ms should emit UserStartedSpeakingFrame."""
        config = MockConfig(vad_confirmation_window_ms=200, vad_enable_confirmation=True)
        vad = VADProcessor(config)
        vad.vad_model = Mock()  # Mock VAD model
        
        # Track pushed frames
        pushed_frames = []
        original_push = vad.push_frame
        
        async def mock_push_frame(frame, direction):
            pushed_frames.append((frame, direction))
        
        vad.push_frame = mock_push_frame
        
        # Simulate sustained voice detection (> 200ms)
        # Mock confidence > threshold for sustained period
        vad.vad_model.return_value = 0.7  # High confidence
        
        # Create mock audio frames
        audio_data = b'\x00\x01' * 512  # 1024 bytes = 512 samples @ 16kHz = ~32ms
        
        # Process multiple frames to simulate sustained voice
        for i in range(10):  # 10 frames * 32ms = 320ms total
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.04)  # Simulate real-time processing
        
        # Wait for confirmation window to expire
        await asyncio.sleep(0.25)  # 250ms > 200ms confirmation
        
        # Check that UserStartedSpeakingFrame was emitted
        started_frames = [f for f, _ in pushed_frames if isinstance(f, UserStartedSpeakingFrame)]
        assert len(started_frames) >= 1, "UserStartedSpeakingFrame should be emitted after 200ms"
    
    @pytest.mark.asyncio
    async def test_false_positive_ignored_voice_stops_early(self):
        """Voice < 200ms should NOT emit UserStartedSpeakingFrame (false positive)."""
        config = MockConfig(vad_confirmation_window_ms=200, vad_enable_confirmation=True)
        vad = VADProcessor(config)
        vad.vad_model = Mock()
        
        # Track pushed frames
        pushed_frames = []
        
        async def mock_push_frame(frame, direction):
            pushed_frames.append((frame, direction))
        
        vad.push_frame = mock_push_frame
        
        # Simulate SHORT voice detection (< 200ms) - FALSE POSITIVE
        audio_data = b'\x00\x01' * 512
        
        # High confidence for 3 frames (96ms)
        vad.vad_model.return_value = 0.7
        for i in range(3):
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.04)
        
        # Then silence (confidence drops)
        vad.vad_model.return_value = 0.1  # Low confidence
        for i in range(5):
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.04)
        
        # Wait to ensure confirmation window would have expired
        await asyncio.sleep(0.25)
        
        # Check that NO UserStartedSpeakingFrame was emitted
        started_frames = [f for f, _ in pushed_frames if isinstance(f, UserStartedSpeakingFrame)]
        assert len(started_frames) == 0, "False positive should be ignored (voice < 200ms)"
    
    @pytest.mark.asyncio
    async def test_confirmation_disabled_immediate_emission(self):
        """With confirmation disabled, UserStartedSpeakingFrame emitted immediately."""
        config = MockConfig(vad_confirmation_window_ms=0, vad_enable_confirmation=False)
        vad = VADProcessor(config)
        vad.vad_model = Mock()
        
        pushed_frames = []
        
        async def mock_push_frame(frame, direction):
            pushed_frames.append((frame, direction))
        
        vad.push_frame = mock_push_frame
        
        # Simulate voice detection
        vad.vad_model.return_value = 0.7
        audio_data = b'\x00\x01' * 512
        
        # Process min_speech_frames (3) to trigger emission
        for i in range(4):
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.01)
        
        # Should emit immediately (legacy behavior)
        started_frames = [f for f, _ in pushed_frames if isinstance(f, UserStartedSpeakingFrame)]
        assert len(started_frames) >= 1, "With confirmation disabled, should emit immediately"
    
    @pytest.mark.asyncio
    async def test_multiple_false_positives_filtered(self):
        """Multiple short bursts < 200ms should all be filtered."""
        config = MockConfig(vad_confirmation_window_ms=200, vad_enable_confirmation=True)
        vad = VADProcessor(config)
        vad.vad_model = Mock()
        
        pushed_frames = []
        
        async def mock_push_frame(frame, direction):
            pushed_frames.append((frame, direction))
        
        vad.push_frame = mock_push_frame
        
        audio_data = b'\x00\x01' * 512
        
        # Simulate 3 short bursts (each < 200ms)
        for burst in range(3):
            # High confidence for 100ms
            vad.vad_model.return_value = 0.7
            for i in range(3):
                frame = AudioFrame(data=audio_data, sample_rate=16000)
                await vad.process_frame(frame, FrameDirection.UPSTREAM)
                await asyncio.sleep(0.04)
            
            # Silence for 100ms
            vad.vad_model.return_value = 0.1
            for i in range(3):
                frame = AudioFrame(data=audio_data, sample_rate=16000)
                await vad.process_frame(frame, FrameDirection.UPSTREAM)
                await asyncio.sleep(0.04)
        
        await asyncio.sleep(0.3)
        
        # All bursts should be filtered (< 200ms each)
        started_frames = [f for f, _ in pushed_frames if isinstance(f, UserStartedSpeakingFrame)]
        assert len(started_frames) == 0, "All false positives should be filtered"
    
    @pytest.mark.asyncio
    async def test_variable_confirmation_windows(self):
        """Test different confirmation window values (100ms, 300ms)."""
        # Test 100ms window
        config_100 = MockConfig(vad_confirmation_window_ms=100, vad_enable_confirmation=True)
        vad_100 = VADProcessor(config_100)
        assert vad_100.confirmation_window_ms == 100
        
        # Test 300ms window
        config_300 = MockConfig(vad_confirmation_window_ms=300, vad_enable_confirmation=True)
        vad_300 = VADProcessor(config_300)
        assert vad_300.confirmation_window_ms == 300
        
        # Test 0ms (disabled)
        config_0 = MockConfig(vad_confirmation_window_ms=0, vad_enable_confirmation=True)
        vad_0 = VADProcessor(config_0)
        assert vad_0.confirmation_window_ms == 0
    
    @pytest.mark.asyncio
    async def test_confirmation_task_cancelled_on_false_positive(self):
        """Confirmation task should be cancelled when voice stops early."""
        config = MockConfig(vad_confirmation_window_ms=200, vad_enable_confirmation=True)
        vad = VADProcessor(config)
        vad.vad_model = Mock()
        
        pushed_frames = []
        
        async def mock_push_frame(frame, direction):
            pushed_frames.append((frame, direction))
        
        vad.push_frame = mock_push_frame
        
        audio_data = b'\x00\x01' * 512
        
        # Start voice detection
        vad.vad_model.return_value = 0.7
        for i in range(3):
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.04)
        
        # Confirmation task should be created
        assert vad._confirmation_task is not None, "Confirmation task should exist"
        assert vad._voice_detected_at is not None, "Voice detection timestamp should be set"
        
        # Voice stops (false positive)
        vad.vad_model.return_value = 0.1
        for i in range(3):
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.04)
        
        await asyncio.sleep(0.1)
        
        # Confirmation task should be cancelled
        assert vad._confirmation_cancelled == True, "Confirmation should be cancelled"
        assert vad._voice_detected_at is None, "Voice timestamp should be cleared"
    
    @pytest.mark.asyncio
    async def test_user_stopped_speaking_still_works(self):
        """UserStoppedSpeakingFrame should still be emitted correctly."""
        config = MockConfig(vad_confirmation_window_ms=200, vad_enable_confirmation=True)
        vad = VADProcessor(config)
        vad.vad_model = Mock()
        
        pushed_frames = []
        
        async def mock_push_frame(frame, direction):
            pushed_frames.append((frame, direction))
        
        vad.push_frame = mock_push_frame
        
        audio_data = b'\x00\x01' * 512
        
        # Sustained voice (> 200ms) - should start
        vad.vad_model.return_value = 0.7
        for i in range(10):
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.04)
        
        await asyncio.sleep(0.25)  # Confirmation
        
        # Now simulate sustained silence (> 500ms default timeout)
        vad.vad_model.return_value = 0.1
        for i in range(20):  # 20 * 32ms = 640ms > 500ms timeout
            frame = AudioFrame(data=audio_data, sample_rate=16000)
            await vad.process_frame(frame, FrameDirection.UPSTREAM)
            await asyncio.sleep(0.04)
        
        # Check both START and STOP frames emitted
        started_frames = [f for f, _ in pushed_frames if isinstance(f, UserStartedSpeakingFrame)]
        stopped_frames = [f for f, _ in pushed_frames if isinstance(f, UserStoppedSpeakingFrame)]
        
        assert len(started_frames) >= 1, "Should emit UserStartedSpeakingFrame"
        assert len(stopped_frames) >= 1, "Should emit UserStoppedSpeakingFrame"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
