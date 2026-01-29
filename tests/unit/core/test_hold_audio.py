"""
Unit tests for HoldAudioPlayer (Module 10).

Tests hold audio loop for UX improvement during async operations.
"""
import pytest
import asyncio
from app.core.audio.hold_audio import HoldAudioPlayer


@pytest.mark.asyncio
async def test_hold_audio_start_stop():
    """Test basic start/stop functionality."""
    player = HoldAudioPlayer()
    
    # Initially not playing
    assert not player.is_playing
    
    # Start playing
    await player.start()
    assert player.is_playing
    
    # Wait briefly
    await asyncio.sleep(0.1)
    
    # Stop
    await player.stop()
    assert not player.is_playing


@pytest.mark.asyncio
async def test_hold_audio_multiple_start():
    """Test multiple start() calls (should be idempotent)."""
    player = HoldAudioPlayer()
    
    await player.start()
    await player.start()  # Should be ignored
    
    assert player.is_playing
    
    await player.stop()


@pytest.mark.asyncio
async def test_hold_audio_stop_without_start():
    """Test stop() without start() (should not crash)."""
    player = HoldAudioPlayer()
    
    # Stop without starting
    await player.stop()  # Should not raise
    
    assert not player.is_playing


@pytest.mark.asyncio
async def test_hold_audio_plays_during_async_operation():
    """Test hold audio plays during simulated async operation."""
    player = HoldAudioPlayer()
    
    # Simulate tool execution
    async def simulate_tool_execution():
        """Simulate 1s tool execution."""
        await asyncio.sleep(1.0)
        return "Tool result"
    
    # Start hold audio
    await player.start()
    
    # Execute tool (async)
    result = await simulate_tool_execution()
    
    # Stop hold audio
    await player.stop()
    
    assert result == "Tool result"
    assert not player.is_playing


@pytest.mark.asyncio
async def test_hold_audio_with_exception():
    """Test hold audio stops even if exception raised."""
    player = HoldAudioPlayer()
    
    try:
        await player.start()
        
        # Simulate tool execution with error
        raise ValueError("Tool execution failed")
    
    except ValueError:
        pass  # Expected
    
    finally:
        await player.stop()
    
    assert not player.is_playing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
