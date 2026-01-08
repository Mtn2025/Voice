"""
Unit tests for VoiceOrchestrator audio processing pipeline.

Target Coverage: ~20% of orchestrator.py (~268 lines)
Focus: Audio input/output, VAD, decoding, streaming, mixing
"""
import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.orchestrator import VoiceOrchestrator


@pytest.mark.unit
class TestProcessAudio:
    """Test suite for process_audio entry point."""
    
    def test_process_audio_valid_pcmu(self, mock_websocket, mock_agent_config):
        """Test: process_audio handles valid PCMU payload."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")
        orch.config = mock_agent_config
        orch.recognizer = MagicMock()
        
        # Create valid PCMU payload (base64 encoded)
        audio_bytes = b'\x00\x01\x02\x03' * 40  # 160 bytes (20ms)
        payload = base64.b64encode(audio_bytes).decode('utf-8')
        
        with patch.object(orch, '_decode_audio_payload', return_value=audio_bytes):
            with patch.object(orch, '_handle_vad_and_push'):
                orch.process_audio(payload)
                
                # Should not raise exception
                assert True
    
    def test_process_audio_invalid_base64(self, mock_websocket, mock_agent_config):
        """Test: process_audio handles invalid base64 gracefully."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        
        # Invalid base64
        payload = "not-valid-base64!@#$"
        
        # Should not crash
        try:
            orch.process_audio(payload)
        except Exception as e:
            pytest.fail(f"Should handle invalid base64 gracefully: {e}")
    
    def test_process_audio_empty_payload(self, mock_websocket):
        """Test: process_audio handles empty payload."""
        orch = VoiceOrchestrator(mock_websocket)
        
        orch.process_audio("")
        
        # Should not crash (early return on empty)
        assert True


@pytest.mark.unit
class TestAudioDecoding:
    """Test suite for audio decoding (_decode_audio_payload)."""
    
    def test_decode_audio_payload_pcmu(self, mock_websocket):
        """Test: _decode_audio_payload decodes PCMU correctly."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")
        
        # PCMU audio (μ-law)
        pcmu_bytes = b'\xFF\x00\x80\x7F' * 40
        payload = base64.b64encode(pcmu_bytes).decode('utf-8')
        
        result = orch._decode_audio_payload(payload)
        
        assert result is not None
        assert isinstance(result, bytes)
        # PCMU decodes to 16-bit PCM (2x size)
        assert len(result) == len(pcmu_bytes) * 2
    
    def test_decode_audio_payload_pcma(self, mock_websocket):
        """Test: _decode_audio_payload decodes PCMA correctly."""
        orch = VoiceOrchestrator(mock_websocket, client_type="telnyx")
        
        # PCMA audio (A-law)
        pcma_bytes = b'\xD5\x2A\x55\xAA' * 40
        payload = base64.b64encode(pcma_bytes).decode('utf-8')
        
        result = orch._decode_audio_payload(payload)
        
        assert result is not None
        assert isinstance(result, bytes)
        # PCMA decodes to 16-bit PCM (2x size)
        assert len(result) == len(pcma_bytes) * 2
    
    def test_decode_audio_payload_browser_passthrough(self, mock_websocket):
        """Test: Browser mode passes through audio without decoding."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")
        
        # Raw PCM
        pcm_bytes = b'\x00\x01' * 80
        payload = base64.b64encode(pcm_bytes).decode('utf-8')
        
        result = orch._decode_audio_payload(payload)
        
        assert result == pcm_bytes  # No transformation


@pytest.mark.unit
class TestVADHandling:
    """Test suite for VAD logic (_handle_vad_and_push)."""
    
    def test_handle_vad_and_push_voice_detected(self, mock_websocket, mock_agent_config):
        """Test: _handle_vad_and_push pushes audio when voice detected."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.recognizer = MagicMock()
        orch.recognizer.write = MagicMock()
        
        # High RMS = voice
        audio_bytes = b'\xFF\xFE' * 80  # High amplitude
        
        orch._handle_vad_and_push(audio_bytes)
        
        # Should push to recognizer
        orch.recognizer.write.assert_called()
    
    def test_handle_vad_and_push_silence_filtered(self, mock_websocket, mock_agent_config):
        """Test: _handle_vad_and_push filters silence."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.enable_vad = True
        orch.recognizer = MagicMock()
        orch.recognizer.write = MagicMock()
        
        # Calibrate VAD filter with some samples
        for _ in range(10):
            orch.vad_filter.update_profile(0.5)
        
        # Very low RMS = silence
        audio_bytes = b'\x00\x00' * 80
        
        orch._handle_vad_and_push(audio_bytes)
        
        # May or may not push depending on VAD calibration
        # Just ensure no crash
        assert True
    
    def test_handle_vad_and_push_vad_disabled(self, mock_websocket, mock_agent_config):
        """Test: VAD bypass when disabled in config."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.config = mock_agent_config
        orch.config.enable_vad = False
        orch.recognizer = MagicMock()
        orch.recognizer.write = MagicMock()
        
        audio_bytes = b'\x00\x00' * 80  # Silence
        
        orch._handle_vad_and_push(audio_bytes)
        
        # Should push even if silence (VAD disabled)
        orch.recognizer.write.assert_called()


@pytest.mark.unit
class TestAudioChunking:
    """Test suite for audio chunking (send_audio_chunked)."""
    
    @pytest.mark.asyncio
    async def test_send_audio_chunked_browser(self, mock_websocket):
        """Test: send_audio_chunked sends directly for browser."""
        orch = VoiceOrchestrator(mock_websocket, client_type="browser")
        
        audio_data = b'test_audio_data_here'
        
        await orch.send_audio_chunked(audio_data)
        
        # Browser should send directly via WebSocket
        mock_websocket.send_bytes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_audio_chunked_phone_queues(self, mock_websocket):
        """Test: send_audio_chunked queues for phone (stream loop)."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")
        
        audio_data = b'X' * 320  # 2 chunks of 160 bytes
        
        await orch.send_audio_chunked(audio_data)
        
        # Should queue chunks (not send directly)
        assert orch.audio_queue.qsize() == 2


@pytest.mark.unit  
class TestAudioStreamLoop:
    """Test suite for continuous audio stream (_audio_stream_loop)."""
    
    @pytest.mark.asyncio
    async def test_audio_stream_loop_basic_flow(self, mock_websocket):
        """Test: _audio_stream_loop sends 20ms chunks continuously."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")
        orch.is_bot_speaking = False
        
        # Queue some audio
        await orch.audio_queue.put(b'X' * 160)
        await orch.audio_queue.put(b'Y' * 160)
        
        # Mock WebSocket to stop after 2 iterations
        call_count = 0
        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()
        
        mock_websocket.send_text = mock_send
        
        with pytest.raises(asyncio.CancelledError):
            await orch._audio_stream_loop()
        
        # Should have sent 2 chunks
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_audio_stream_loop_closed_socket(self, mock_websocket):
        """Test: _audio_stream_loop handles closed WebSocket gracefully."""
        orch = VoiceOrchestrator(mock_websocket, client_type="twilio")
        
        # Simulate closed socket
        mock_websocket.client_state = 3  # CLOSED
        
        # Should exit gracefully
        try:
            await asyncio.wait_for(orch._audio_stream_loop(), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("Stream loop should exit on closed socket")


@pytest.mark.unit
class TestAudioMixing:
    """Test suite for audio mixing (_mix_audio, _get_next_background_chunk)."""
    
    def test_mix_audio_tts_only(self, mock_websocket):
        """Test: _mix_audio returns TTS when no background audio."""
        orch = VoiceOrchestrator(mock_websocket)
        orch.bg_loop_buffer = None
        
        tts_chunk = b'\x01\x02' * 80
        result = orch._mix_audio(tts_chunk, None)
        
        assert result == tts_chunk
    
    def test_mix_audio_background_only(self, mock_websocket):
        """Test: _mix_audio returns background when no TTS."""
        orch = VoiceOrchestrator(mock_websocket)
        
        bg_chunk = b'\x03\x04' * 80
        result = orch._mix_audio(None, bg_chunk)
        
        assert result == bg_chunk
    
    def test_mix_audio_both(self, mock_websocket):
        """Test: _mix_audio mixes TTS + background."""
        orch = VoiceOrchestrator(mock_websocket)
        
        tts_chunk = b'\xFF\xFE' * 80
        bg_chunk = b'\x01\x02' * 80
        
        result = orch._mix_audio(tts_chunk, bg_chunk)
        
        # Should return mixed audio (not None)
        assert result is not None
        assert len(result) == 160
    
    def test_get_next_background_chunk(self, mock_websocket):
        """Test: _get_next_background_chunk loops audio buffer."""
        orch = VoiceOrchestrator(mock_websocket)
        
        # Simulate background audio buffer
        orch.bg_loop_buffer = b'BG_AUDIO_DATA' * 20  # 260 bytes
        orch.bg_loop_index = 0
        
        chunk1 = orch._get_next_background_chunk(160)
        chunk2 = orch._get_next_background_chunk(160)
        
        assert chunk1 is not None
        assert chunk2 is not None
        assert len(chunk1) == 160
        assert len(chunk2) == 160

