"""Unit tests for Value Objects."""
import pytest
from app.domain.value_objects import (
    VoiceConfig,
    AudioFormat,
    ContactInfo,
    CallMetadata
)


class TestVoiceConfig:
    """Tests for VoiceConfig value object."""
    
    def test_create_voice_config_with_defaults(self):
        """Test creating VoiceConfig with default values."""
        config = VoiceConfig(name="es-MX-DaliaNeural")
        
        assert config.name == "es-MX-DaliaNeural"
        assert config.speed == 1.0
        assert config.pitch == 0
        assert config.volume == 100
        assert config.style == "default"
        assert config.style_degree == 1.0
    
    def test_voice_config_is_immutable(self):
        """Test that VoiceConfig is immutable (frozen)."""
        config = VoiceConfig(name="test")
        
        with pytest.raises(Exception):  # FrozenInstanceError
            config.speed = 2.0
    
    def test_voice_config_validation_speed(self):
        """Test speed validation (must be 0.5-2.0)."""
        with pytest.raises(ValueError, match="Speed must be between"):
            VoiceConfig(name="test", speed=3.0)
        
        with pytest.raises(ValueError):
            VoiceConfig(name="test", speed=0.1)
    
    def test_voice_config_validation_pitch(self):
        """Test pitch validation (must be -100 to +100)."""
        with pytest.raises(ValueError, match="Pitch must be between"):
            VoiceConfig(name="test", pitch=150)
        
        with pytest.raises(ValueError):
            VoiceConfig(name="test", pitch=-150)
    
    def test_voice_config_to_ssml_params(self):
        """Test conversion to SSML parameters."""
        config = VoiceConfig(
            name="es-MX-DaliaNeural",
            speed=1.2,
            pitch=5,
            volume=50,
            style="friendly",
            style_degree=1.5
        )
        
        params = config.to_ssml_params()
        
        assert params["voice_name"] == "es-MX-DaliaNeural"
        assert params["rate"] == 1.2
        assert params["pitch"] == 5
        assert params["volume"] == 50
        assert params["style"] == "friendly"
        assert params["style_degree"] == 1.5
    
    def test_voice_config_to_ssml_params_default_style(self):
        """Test SSML params with default style (should be None)."""
        config = VoiceConfig(name="test")
        params = config.to_ssml_params()
        
        assert params["style"] is None
        assert params["style_degree"] is None


class TestAudioFormat:
    """Tests for AudioFormat value object."""
    
    def test_telephony_format(self):
        """Test telephony format detection."""
        format = AudioFormat(sample_rate=8000, encoding="mulaw")
        
        assert format.is_telephony
        assert not format.is_browser
    
    def test_browser_format(self):
        """Test browser format detection."""
        format = AudioFormat(sample_rate=16000, encoding="pcm")
        
        assert format.is_browser
        assert not format.is_telephony
    
    def test_for_client_type_factory(self):
        """Test factory method for different client types."""
        browser_format = AudioFormat.for_client_type("browser")
        assert browser_format.sample_rate == 16000
        assert browser_format.encoding == "pcm"
        
        twilio_format = AudioFormat.for_client_type("twilio")
        assert twilio_format.sample_rate == 8000
        assert twilio_format.encoding == "mulaw"
        
        telnyx_format = AudioFormat.for_client_type("telnyx")
        assert telnyx_format.sample_rate == 8000


class TestContactInfo:
    """Tests for ContactInfo value object."""
    
    def test_create_contact_info(self):
        """Test creating ContactInfo."""
        contact = ContactInfo(
            name="Juan Pérez",
            phone="+525551234567",
            company="Acme Corp"
        )
        
        assert contact.name == "Juan Pérez"
        assert contact.has_data
    
    def test_contact_info_to_prompt_context(self):
        """Test formatting contact info for prompt."""
        contact = ContactInfo(
            name="Ana García",
            company="Tech Inc",
            notes="VIP client"
        )
        
        context = contact.to_prompt_context()
        
        assert "Ana García" in context
        assert "Tech Inc" in context
        assert "VIP client" in context
        assert "Cliente:" in context
        assert "Empresa:" in context
    
    def test_contact_info_empty(self):
        """Test empty contact info."""
        contact = ContactInfo()
        
        assert not contact.has_data
        assert contact.to_prompt_context() == ""


class TestCallMetadata:
    """Tests for CallMetadata value object."""
    
    def test_create_call_metadata(self):
        """Test creating CallMetadata."""
        metadata = CallMetadata(
            session_id="test-123",
            client_type="twilio",
            phone_number="+525551234567"
        )
        
        assert metadata.session_id == "test-123"
        assert metadata.is_inbound
        assert metadata.is_telephony
        assert not metadata.is_browser
    
    def test_call_metadata_browser(self):
        """Test browser call metadata."""
        metadata = CallMetadata(
            session_id="test-456",
            client_type="browser"
        )
        
        assert metadata.is_browser
        assert not metadata.is_inbound
        assert not metadata.is_telephony
    
    def test_call_metadata_outbound(self):
        """Test outbound call metadata."""
        metadata = CallMetadata(
            session_id="test-789",
            client_type="twilio",
            campaign_id="campaign-001"
        )
        
        assert metadata.is_outbound
        assert not metadata.is_inbound  # No phone_number
    
    def test_call_metadata_duration(self):
        """Test duration calculation."""
        metadata = CallMetadata(
            session_id="test",
            client_type="browser"
        )
        
        # Duration should be >= 0
        assert metadata.duration_seconds >= 0
