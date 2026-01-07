"""
Configuration Schemas for Dashboard - Punto A8

Pydantic schemas for validating configuration updates by profile.
Replaces monolithic Form endpoint with type-safe, modular schemas.
"""

from typing import Optional

from pydantic import BaseModel, Field


class BrowserConfigUpdate(BaseModel):
    """
    Browser/Simulator profile configuration.
    
    All fields are optional (partial update with PATCH).
    """
    # LLM Configuration
    system_prompt: Optional[str] = Field(None, max_length=10000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llm_model: Optional[str] = Field(None, max_length=100)
    
    # Voice Configuration
    voice_name: Optional[str] = Field(None, max_length=100)
    voice_style: Optional[str] = Field(None, max_length=50)
    voice_speed: Optional[float] = Field(None, ge=0.5, le=2.0)
    voice_pacing_ms: Optional[int] = Field(None, ge=0, le=2000)
    
    # STT Configuration
    stt_language: Optional[str] = Field(None, max_length=10)
    
    # Behavior
    background_sound: Optional[str] = Field(None, max_length=50)
    idle_timeout: Optional[float] = Field(None, ge=5.0, le=120.0)
    idle_message: Optional[str] = Field(None, max_length=500)
    inactivity_max_retries: Optional[int] = Field(None, ge=1, le=10)
    max_duration: Optional[int] = Field(None, ge=60, le=3600)
    interruption_threshold: Optional[int] = Field(None, ge=0, le=20)
    
    # Messages
    first_message: Optional[str] = Field(None, max_length=500)
    first_message_mode: Optional[str] = Field(None, max_length=50)
    
    # Advanced
    hallucination_blacklist: Optional[str] = Field(None, max_length=500)
    
    class Config:
        # Allow extra fields (for future compatibility)
        extra = "ignore"


class TwilioConfigUpdate(BaseModel):
    """
    Twilio/Phone profile configuration.
    
    All fields are optional (partial update with PATCH).
    Suffix '_phone' matches database column names.
    """
    # LLM Configuration
    system_prompt_phone: Optional[str] = Field(None, max_length=10000)
    llm_provider_phone: Optional[str] = Field(None, max_length=50)
    llm_model_phone: Optional[str] = Field(None, max_length=100)
    temperature_phone: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens_phone: Optional[int] = Field(None, ge=1, le=4096)
    
    # Voice Configuration
    voice_name_phone: Optional[str] = Field(None, max_length=100)
    voice_style_phone: Optional[str] = Field(None, max_length=50)
    voice_speed_phone: Optional[float] = Field(None, ge=0.5, le=2.0)
    voice_pacing_ms_phone: Optional[int] = Field(None, ge=0, le=2000)
    
    # STT Configuration
    stt_provider_phone: Optional[str] = Field(None, max_length=50)
    stt_language_phone: Optional[str] = Field(None, max_length=10)
    input_min_characters_phone: Optional[int] = Field(None, ge=1, le=100)
    
    # Audio Processing
    enable_denoising_phone: Optional[bool] = None
    interruption_threshold_phone: Optional[int] = Field(None, ge=0, le=20)
    
    # Messages
    first_message_phone: Optional[str] = Field(None, max_length=500)
    first_message_mode_phone: Optional[str] = Field(None, max_length=50)
    
    # Twilio-Specific
    twilio_machine_detection: Optional[str] = Field(None, max_length=50)
    twilio_record: Optional[bool] = None
    twilio_recording_channels: Optional[str] = Field(None, max_length=20)
    twilio_trim_silence: Optional[bool] = None
    initial_silence_timeout_ms_phone: Optional[int] = Field(None, ge=1000, le=60000)
    
    # Advanced
    hallucination_blacklist_phone: Optional[str] = Field(None, max_length=500)
    
    class Config:
        extra = "ignore"


class TelnyxConfigUpdate(BaseModel):
    """
    Telnyx profile configuration.
    
    All fields are optional (partial update with PATCH).
    Suffix '_telnyx' matches database column names.
    """
    # LLM Configuration
    system_prompt_telnyx: Optional[str] = Field(None, max_length=10000)
    llm_provider_telnyx: Optional[str] = Field(None, max_length=50)
    llm_model_telnyx: Optional[str] = Field(None, max_length=100)
    temperature_telnyx: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens_telnyx: Optional[int] = Field(None, ge=1, le=4096)
    
    # Voice Configuration
    voice_name_telnyx: Optional[str] = Field(None, max_length=100)
    voice_style_telnyx: Optional[str] = Field(None, max_length=50)
    voice_speed_telnyx: Optional[float] = Field(None, ge=0.5, le=2.0)
    voice_pacing_ms_telnyx: Optional[int] = Field(None, ge=0, le=2000)
    voice_sensitivity_telnyx: Optional[int] = Field(None, ge=1000, le=10000)
    
    # STT Configuration
    stt_provider_telnyx: Optional[str] = Field(None, max_length=50)
    stt_language_telnyx: Optional[str] = Field(None, max_length=10)
    input_min_characters_telnyx: Optional[int] = Field(None, ge=1, le=100)
    
    # Audio Processing
    enable_denoising_telnyx: Optional[bool] = None
    enable_krisp_telnyx: Optional[bool] = None
    enable_vad_telnyx: Optional[bool] = None
    silence_timeout_ms_telnyx: Optional[int] = Field(None, ge=500, le=5000)
    interruption_threshold_telnyx: Optional[int] = Field(None, ge=0, le=20)
    
    # Messages
    first_message_telnyx: Optional[str] = Field(None, max_length=500)
    first_message_mode_telnyx: Optional[str] = Field(None, max_length=50)
    idle_message_telnyx: Optional[str] = Field(None, max_length=500)
    
    # Behavior
    idle_timeout_telnyx: Optional[float] = Field(None, ge=5.0, le=120.0)
    max_duration_telnyx: Optional[int] = Field(None, ge=60, le=3600)
    initial_silence_timeout_ms_telnyx: Optional[int] = Field(None, ge=1000, le=60000)
    
    # Recording & AMD
    enable_recording_telnyx: Optional[bool] = None
    amd_config_telnyx: Optional[str] = Field(None, max_length=50)
    
    # Advanced
    hallucination_blacklist_telnyx: Optional[str] = Field(None, max_length=500)
    
    class Config:
        extra = "ignore"


class CoreConfigUpdate(BaseModel):
    """
    Core/Global configuration.
    
    Provider selection and extraction model.
    """
    stt_provider: Optional[str] = Field(None, max_length=50)
    llm_provider: Optional[str] = Field(None, max_length=50)
    tts_provider: Optional[str] = Field(None, max_length=50)
    extraction_model: Optional[str] = Field(None, max_length=100)
    
    class Config:
        extra = "ignore"
