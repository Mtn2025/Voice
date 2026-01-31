"""
Tests for ProfileConfig abstraction layer.

Verifies that:
1. get_profile() returns correct values for each profile type
2. update_profile() modifies only the target profile
3. Profiles are isolated (updating one doesn't affect others)
4. Type validation works via Pydantic
"""

import pytest
from pydantic import ValidationError
from app.db.models import AgentConfig
from app.schemas.profile_config import ProfileConfigSchema


class TestProfileConfigSuffix:
    """Test _get_suffix() method."""
    
    def test_browser_suffix(self):
        """Browser profile should have empty suffix."""
        config = AgentConfig()
        assert config._get_suffix("browser") == ""
    
    def test_simulator_suffix(self):
        """Simulator should use browser config (empty suffix)."""
        config = AgentConfig()
        assert config._get_suffix("simulator") == ""
    
    def test_twilio_suffix(self):
        """Twilio should use _phone suffix."""
        config = AgentConfig()
        assert config._get_suffix("twilio") == "_phone"
    
    def test_telnyx_suffix(self):
        """Telnyx should use _telnyx suffix."""
        config = AgentConfig()
        assert config._get_suffix("telnyx") == "_telnyx"
    
    def test_unknown_profile(self):
        """Unknown profiles should default to empty suffix."""
        config = AgentConfig()
        assert config._get_suffix("unknown") == ""
    
    def test_case_insensitive(self):
        """Suffix mapping should be case-insensitive."""
        config = AgentConfig()
        assert config._get_suffix("TWILIO") == "_phone"
        assert config._get_suffix("Telnyx") == "_telnyx"


class TestGetProfile:
    """Test get_profile() method."""
    
    def test_get_browser_profile(self):
        """Should return browser profile values."""
        config = AgentConfig(
            voice_speed=1.0,
            voice_speed_phone=0.9,
            voice_speed_telnyx=0.85,
            temperature=0.7,
            temperature_phone=0.6,
            temperature_telnyx=0.65
        )
        
        profile = config.get_profile("browser")
        
        assert profile.voice_speed == 1.0
        assert profile.temperature == 0.7
    
    def test_get_twilio_profile(self):
        """Should return twilio profile values (_phone suffix)."""
        config = AgentConfig(
            voice_speed=1.0,
            voice_speed_phone=0.9,
            voice_speed_telnyx=0.85,
            temperature=0.7,
            temperature_phone=0.6,
            temperature_telnyx=0.65
        )
        
        profile = config.get_profile("twilio")
        
        assert profile.voice_speed == 0.9
        assert profile.temperature == 0.6
    
    def test_get_telnyx_profile(self):
        """Should return telnyx profile values (_telnyx suffix)."""
        config = AgentConfig(
            voice_speed=1.0,
            voice_speed_phone=0.9,
            voice_speed_telnyx=0.85,
            temperature=0.7,
            temperature_phone=0.6,
            temperature_telnyx=0.65
        )
        
        profile = config.get_profile("telnyx")
        
        assert profile.voice_speed == 0.85
        assert profile.temperature == 0.65
    
    def test_get_profile_with_defaults(self):
        """Should use Pydantic defaults for None values."""
        config = AgentConfig()  # All columns None
        
        profile = config.get_profile("browser")
        
        # Pydantic defaults (from schema)
        assert profile.stt_provider is None  # No default in schema
        assert profile.model_config["validate_assignment"] is True
    
    def test_get_profile_returns_pydantic_schema(self):
        """Should return ProfileConfigSchema instance."""
        config = AgentConfig()
        profile = config.get_profile("browser")
        
        assert isinstance(profile, ProfileConfigSchema)


class TestUpdateProfile:
    """Test update_profile() method."""
    
    def test_update_browser_profile(self):
        """Should update browser profile only."""
        config = AgentConfig(
            voice_speed=1.0,
            voice_speed_phone=0.9,
            voice_speed_telnyx=0.85
        )
        
        updates = ProfileConfigSchema(voice_speed=1.2)
        config.update_profile("browser", updates)
        
        # Browser updated
        assert config.voice_speed == 1.2
        # Twilio and Telnyx NOT affected
        assert config.voice_speed_phone == 0.9
        assert config.voice_speed_telnyx == 0.85
    
    def test_update_twilio_profile(self):
        """Should update twilio profile only (_phone suffix)."""
        config = AgentConfig(
            voice_speed=1.0,
            voice_speed_phone=0.9,
            voice_speed_telnyx=0.85
        )
        
        updates = ProfileConfigSchema(voice_speed=1.5)
        config.update_profile("twilio", updates)
        
        # Twilio updated
        assert config.voice_speed_phone == 1.5
        # Browser and Telnyx NOT affected
        assert config.voice_speed == 1.0
        assert config.voice_speed_telnyx == 0.85
    
    def test_update_telnyx_profile(self):
        """Should update telnyx profile only (_telnyx suffix)."""
        config = AgentConfig(
            voice_speed=1.0,
            voice_speed_phone=0.9,
            voice_speed_telnyx=0.85
        )
        
        updates = ProfileConfigSchema(voice_speed=0.95)
        config.update_profile("telnyx", updates)
        
        # Telnyx updated
        assert config.voice_speed_telnyx == 0.95
        # Browser and Twilio NOT affected
        assert config.voice_speed == 1.0
        assert config.voice_speed_phone == 0.9
    
    def test_update_multiple_fields(self):
        """Should update multiple fields at once."""
        config = AgentConfig(
            voice_speed=1.0,
            temperature=0.7,
            context_window=10,
            voice_speed_phone=0.9,
            temperature_phone=0.6,
            context_window_phone=8
        )
        
        updates = ProfileConfigSchema(
            voice_speed=1.2,
            temperature=0.8,
            context_window=15
        )
        config.update_profile("browser", updates)
        
        # All browser fields updated
        assert config.voice_speed == 1.2
        assert config.temperature == 0.8
        assert config.context_window == 15
        
        # Twilio NOT affected
        assert config.voice_speed_phone == 0.9
        assert config.temperature_phone == 0.6
        assert config.context_window_phone == 8
    
    def test_partial_update_exclude_unset(self):
        """Should only update explicitly set fields (exclude_unset=True)."""
        config = AgentConfig(
            voice_speed=1.0,
            temperature=0.7
        )
        
        # Only set voice_speed (temperature uses Pydantic default but is not set)
        updates = ProfileConfigSchema(voice_speed=1.5)
        config.update_profile("browser", updates)
        
        # voice_speed updated
        assert config.voice_speed == 1.5
        # temperature NOT updated (stays original value)
        assert config.temperature == 0.7


class TestProfileIsolation:
    """Test that profiles don't interfere with each other."""
    
    def test_full_isolation(self):
        """Comprehensive isolation test."""
        config = AgentConfig(
            # Browser
            voice_speed=1.0,
            temperature=0.7,
            stt_language="es-MX",
            # Twilio
            voice_speed_phone=0.9,
            temperature_phone=0.6,
            stt_language_phone="en-US",
            # Telnyx
            voice_speed_telnyx=0.85,
            temperature_telnyx=0.65,
            stt_language_telnyx="pt-BR"
        )
        
        # Update each profile
        browser_updates = ProfileConfigSchema(voice_speed=1.2, temperature=0.8)
        config.update_profile("browser", browser_updates)
        
        twilio_updates = ProfileConfigSchema(voice_speed=0.95, temperature=0.55)
        config.update_profile("twilio", twilio_updates)
        
        telnyx_updates = ProfileConfigSchema(voice_speed=0.88, temperature=0.68)
        config.update_profile("telnyx", telnyx_updates)
        
        # Verify each profile independently
        browser_profile = config.get_profile("browser")
        assert browser_profile.voice_speed == 1.2
        assert browser_profile.temperature == 0.8
        assert browser_profile.stt_language == "es-MX"
        
        twilio_profile = config.get_profile("twilio")
        assert twilio_profile.voice_speed == 0.95
        assert twilio_profile.temperature == 0.55
        assert twilio_profile.stt_language == "en-US"
        
        telnyx_profile = config.get_profile("telnyx")
        assert telnyx_profile.voice_speed == 0.88
        assert telnyx_profile.temperature == 0.68
        assert telnyx_profile.stt_language == "pt-BR"


class TestValidation:
    """Test Pydantic validation via ProfileConfigSchema."""
    
    def test_voice_speed_validation(self):
        """Should validate voice_speed range."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfigSchema(voice_speed=3.0)
        # Verify it's a validation error for voice_speed field
        assert "voice_speed" in str(exc_info.value)
    
    def test_temperature_validation(self):
        """Should validate temperature range."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfigSchema(temperature=5.0)
        assert "temperature" in str(exc_info.value)
    
    def test_context_window_validation(self):
        """Should validate context_window range."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfigSchema(context_window=100)
        assert "context_window" in str(exc_info.value)
    
    def test_vad_threshold_validation(self):
        """Should validate vad_threshold range."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfigSchema(vad_threshold=1.5)
        assert "vad_threshold" in str(exc_info.value)
    
    def test_valid_values_pass(self):
        """Valid values should not raise errors."""
        # Should not raise
        schema = ProfileConfigSchema(
            voice_speed=1.0,
            temperature=0.7,
            context_window=10,
            vad_threshold=0.5
        )
        
        assert schema.voice_speed == 1.0
        assert schema.temperature == 0.7
        assert schema.context_window == 10
        assert schema.vad_threshold == 0.5


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires db_session fixture - not critical for ProfileConfig unit tests")
class TestIntegration:
    """Integration tests with database (requires DB setup)."""
    
    async def test_round_trip(self, db_session):
        """Test get_profile -> modify -> update_profile -> get_profile."""
        # This test requires a real database session
        # Skipped for now (requires test fixtures)
        pass
