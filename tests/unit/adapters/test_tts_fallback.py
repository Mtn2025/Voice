"""
Unit tests for TTSWithFallback (Module 11 - Resilience).

Tests automatic fallback on primary TTS failure.
"""
import pytest
from app.adapters.outbound.tts.tts_with_fallback import TTSWithFallback
from app.domain.ports import TTSRequest, TTSException


class MockTTSPort:
    """Mock TTS adapter for testing."""
    
    def __init__(self, name, should_fail=False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0
    
    async def synthesize(self, request):
        """Mock synthesis."""
        self.call_count += 1
        
        if self.should_fail:
            raise TTSException(f"{self.name} TTS failed (mock)")
        
        # Success: yield mock audio
        yield b"MOCK_AUDIO_" + self.name.encode()
    
    async def get_available_voices(self):
        return [f"{self.name}_voice"]
    
    def is_voice_available(self, voice_name):
        return True


@pytest.mark.asyncio
async def test_tts_fallback_uses_primary_when_working():
    """Test that primary TTS is used when it works."""
    primary = MockTTSPort("Primary", should_fail=False)
    fallback = MockTTSPort("Fallback", should_fail=False)
    
    tts = TTSWithFallback(primary=primary, fallback=fallback)
    
    request = TTSRequest(text="Hello", voice_id="test")
    
    # Should use primary
    chunks = []
    async for chunk in tts.synthesize(request):
        chunks.append(chunk)
    
    assert len(chunks) == 1
    assert chunks[0] == b"MOCK_AUDIO_Primary"
    assert primary.call_count == 1
    assert fallback.call_count == 0  # Fallback NOT used


@pytest.mark.asyncio
async def test_tts_fallback_uses_fallback_on_primary_fail():
    """Test fallback is used when primary fails."""
    primary = MockTTSPort("Primary", should_fail=True)
    fallback = MockTTSPort("Fallback", should_fail=False)
    
    tts = TTSWithFallback(primary=primary, fallback=fallback)
    
    request = TTSRequest(text="Hello", voice_id="test")
    
    # Should fallback to fallback TTS
    chunks = []
    async for chunk in tts.synthesize(request):
        chunks.append(chunk)
    
    assert len(chunks) == 1
    assert chunks[0] == b"MOCK_AUDIO_Fallback"
    assert primary.call_count == 1
    assert fallback.call_count == 1  # Fallback used


@pytest.mark.asyncio
async def test_tts_fallback_circuit_breaker():
    """Test circuit breaker activates after 3 failures."""
    primary = MockTTSPort("Primary", should_fail=True)
    fallback = MockTTSPort("Fallback", should_fail=False)
    
    tts = TTSWithFallback(primary=primary, fallback=fallback)
    
    request = TTSRequest(text="Hello", voice_id="test")
    
    # Call 3 times (threshold)
    for _ in range(3):
        chunks = []
        async for chunk in tts.synthesize(request):
            chunks.append(chunk)
    
    # Should be in fallback mode now
    assert tts.is_using_fallback
    assert tts.failure_count == 3
    
    # 4th call: Should skip primary entirely
    primary.call_count = 0  # Reset
    chunks = []
    async for chunk in tts.synthesize(request):
        chunks.append(chunk)
    
    assert primary.call_count == 0  # Primary NOT tried (fallback mode active)
    assert fallback.call_count == 4  # Fallback used directly


@pytest.mark.asyncio
async def test_tts_fallback_both_fail():
    """Test exception is raised when BOTH primary AND fallback fail."""
    primary = MockTTSPort("Primary", should_fail=True)
    fallback = MockTTSPort("Fallback", should_fail=True)
    
    tts = TTSWithFallback(primary=primary, fallback=fallback)
    
    request = TTSRequest(text="Hello", voice_id="test")
    
    # Should raise exception
    with pytest.raises(TTSException) as exc_info:
        async for chunk in tts.synthesize(request):
            pass
    
    assert "complete failure" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
