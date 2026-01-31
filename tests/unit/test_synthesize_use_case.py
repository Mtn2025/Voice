"""Unit tests for SynthesizeTextUseCase."""
import pytest
from unittest.mock import Mock, AsyncMock
from app.use_cases.voice.synthesize_text import SynthesizeTextUseCase
from app.domain.value_objects.voice_config import VoiceConfig


@pytest.mark.asyncio
async def test_synthesize_text_success():
    """Test successful text synthesis."""
    # Arrange
    mock_tts = Mock()
    mock_tts.synthesize_ssml = AsyncMock(return_value=b"audio_data_12345")
    
    use_case = SynthesizeTextUseCase(mock_tts)
    voice_config = VoiceConfig(name="es-MX-DaliaNeural", speed=1.2)
    
    # Act
    result = await use_case.execute("Hola mundo", voice_config)
    
    # Assert
    assert result == b"audio_data_12345"
    mock_tts.synthesize_ssml.assert_called_once()
    
    # Verify SSML contains voice and text
    call_args = mock_tts.synthesize_ssml.call_args[0][0]
    assert "Hola mundo" in call_args
    assert "es-MX-DaliaNeural" in call_args
    assert 'rate="1.2"' in call_args


@pytest.mark.asyncio
async def test_synthesize_empty_text():
    """Test that empty text returns empty bytes."""
    mock_tts = Mock()
    use_case = SynthesizeTextUseCase(mock_tts)
    voice_config = VoiceConfig(name="test")
    
    result = await use_case.execute("", voice_config)
    
    assert result == b""
    mock_tts.synthesize_ssml.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_whitespace_only():
    """Test that whitespace-only text returns empty bytes."""
    mock_tts = Mock()
    use_case = SynthesizeTextUseCase(mock_tts)
    voice_config = VoiceConfig(name="test")
    
    result = await use_case.execute("   \n\t  ", voice_config)
    
    assert result == b""


@pytest.mark.asyncio
async def test_synthesize_with_style():
    """Test synthesis with voice style."""
    mock_tts = Mock()
    mock_tts.synthesize_ssml = AsyncMock(return_value=b"audio")
    
    use_case = SynthesizeTextUseCase(mock_tts)
    voice_config = VoiceConfig(
        name="es-MX-DaliaNeural",
        style="friendly",
        style_degree=1.5
    )
    
    _result = await use_case.execute("Hello", voice_config)
    
    # Verify SSML includes style
    ssml = mock_tts.synthesize_ssml.call_args[0][0]
    assert 'mstts:express-as' in ssml
    assert 'style="friendly"' in ssml
    assert 'styledegree="1.5"' in ssml


@pytest.mark.asyncio
async def test_synthesize_with_fallback_success():
    """Test fallback mechanism when primary fails."""
    mock_tts = Mock()
    # First call fails, second succeeds
    mock_tts.synthesize_ssml = AsyncMock(side_effect=[
        Exception("Primary failed"),
        b"fallback_audio"
    ])
    
    use_case = SynthesizeTextUseCase(mock_tts)
    voice_config = VoiceConfig(name="test")
    
    result = await use_case.execute_with_fallback(
        "Primary text",
        voice_config,
        fallback_text="Fallback text"
    )
    
    assert result == b"fallback_audio"
    assert mock_tts.synthesize_ssml.call_count == 2


@pytest.mark.asyncio
async def test_synthesize_with_fallback_no_fallback_text():
    """Test that exception propagates when no fallback provided."""
    mock_tts = Mock()
    mock_tts.synthesize_ssml = AsyncMock(side_effect=Exception("Synthesis failed"))
    
    use_case = SynthesizeTextUseCase(mock_tts)
    voice_config = VoiceConfig(name="test")
    
    with pytest.raises(Exception, match="Synthesis failed"):
        await use_case.execute_with_fallback("Text", voice_config, fallback_text=None)
