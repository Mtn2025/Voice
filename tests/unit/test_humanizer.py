import pytest
import asyncio
from app.processors.logic.humanizer import HumanizerProcessor
from app.core.frames import TextFrame
from app.core.processor import FrameDirection

class MockConfig:
    def __init__(self, enabled=False):
        self.voice_filler_injection = enabled

@pytest.mark.asyncio
async def test_humanizer_injection_enabled():
    config = MockConfig(enabled=True)
    processor = HumanizerProcessor(config)
    # Force filler choice to be predictable for test? 
    # Or just check if length increases or starts with one of the fillers.
    processor.fillers = ["TEST_FILLER"] 
    
    # Text > 10 chars
    frame = TextFrame(text="Hola, esto es una prueba de texto largo.")
    
    # Mock push_frame to capture output
    output_frames = []
    async def mock_push(frame, direction):
        output_frames.append(frame)
    processor.push_frame = mock_push
    
    # Mocking random.random to return 0.1 (always < 0.2) to guarantee injection
    from unittest.mock import patch
    
    with patch('app.processors.logic.humanizer.random.random', return_value=0.1):
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)
        
    # Should be injected immediately
    assert "TEST_FILLER" in output_frames[0].text, "Filler should be injected when random < 0.2"

@pytest.mark.asyncio
async def test_humanizer_injection_disabled():
    config = MockConfig(enabled=False)
    processor = HumanizerProcessor(config)
    processor.fillers = ["TEST_FILLER"]
    
    frame = TextFrame(text="Hola, esto es una prueba de texto largo.")
    
    output_frames = []
    async def mock_push(frame, direction):
        output_frames.append(frame)
    processor.push_frame = mock_push
    
    # Run many times, ensure NEVER injected
    for _ in range(20):
        output_frames.clear()
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)
        assert "TEST_FILLER" not in output_frames[0].text
        
    print("✅ Disabled config prevents injection")

if __name__ == "__main__":
    # Manual run helper
    async def run():
        await test_humanizer_injection_enabled()
        await test_humanizer_injection_disabled()
        print("✅ All Humanizer tests passed")
    asyncio.run(run())
