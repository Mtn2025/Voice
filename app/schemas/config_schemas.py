"""
Configuration Schemas for Dashboard - Punto A8

Pydantic schemas for validating configuration updates by profile.
Replaces monolithic Form endpoint with type-safe, modular schemas.
"""


from pydantic import BaseModel, Field


class BrowserConfigUpdate(BaseModel):
    """
    Browser/Simulator profile configuration.

    All fields are optional (partial update with PATCH).
    """
    # LLM Configuration
    system_prompt: str | None = Field(None, max_length=10000)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    llm_model: str | None = Field(None, max_length=100)

    # Voice Configuration
    voice_name: str | None = Field(None, max_length=100)
    voice_style: str | None = Field(None, max_length=50)
    voice_speed: float | None = Field(None, ge=0.5, le=2.0)
    voice_pacing_ms: int | None = Field(None, ge=0, le=2000)

    # STT Configuration
    stt_language: str | None = Field(None, max_length=10)

    # Behavior
    background_sound: str | None = Field(None, max_length=50)
    idle_timeout: float | None = Field(None, ge=5.0, le=120.0)
    idle_message: str | None = Field(None, max_length=500)
    inactivity_max_retries: int | None = Field(None, ge=1, le=10)
    max_duration: int | None = Field(None, ge=60, le=3600)
    interruption_threshold: int | None = Field(None, ge=0, le=20)

    # Messages
    first_message: str | None = Field(None, max_length=500)
    first_message_mode: str | None = Field(None, max_length=50)

    # Advanced
    hallucination_blacklist: str | None = Field(None, max_length=500)

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
    system_prompt_phone: str | None = Field(None, max_length=10000)
    llm_provider_phone: str | None = Field(None, max_length=50)
    llm_model_phone: str | None = Field(None, max_length=100)
    temperature_phone: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens_phone: int | None = Field(None, ge=1, le=4096)

    # Voice Configuration
    voice_name_phone: str | None = Field(None, max_length=100)
    voice_style_phone: str | None = Field(None, max_length=50)
    voice_speed_phone: float | None = Field(None, ge=0.5, le=2.0)
    voice_pacing_ms_phone: int | None = Field(None, ge=0, le=2000)

    # STT Configuration
    stt_provider_phone: str | None = Field(None, max_length=50)
    stt_language_phone: str | None = Field(None, max_length=10)
    input_min_characters_phone: int | None = Field(None, ge=1, le=100)

    # Audio Processing
    enable_denoising_phone: bool | None = None
    interruption_threshold_phone: int | None = Field(None, ge=0, le=20)

    # Messages
    first_message_phone: str | None = Field(None, max_length=500)
    first_message_mode_phone: str | None = Field(None, max_length=50)

    # Twilio-Specific
    twilio_machine_detection: str | None = Field(None, max_length=50)
    twilio_record: bool | None = None
    twilio_recording_channels: str | None = Field(None, max_length=20)
    twilio_trim_silence: bool | None = None
    initial_silence_timeout_ms_phone: int | None = Field(None, ge=1000, le=60000)

    # Advanced
    hallucination_blacklist_phone: str | None = Field(None, max_length=500)

    class Config:
        extra = "ignore"


class TelnyxConfigUpdate(BaseModel):
    """
    Telnyx profile configuration.

    All fields are optional (partial update with PATCH).
    Suffix '_telnyx' matches database column names.
    """
    # LLM Configuration
    system_prompt_telnyx: str | None = Field(None, max_length=10000)
    llm_provider_telnyx: str | None = Field(None, max_length=50)
    llm_model_telnyx: str | None = Field(None, max_length=100)
    temperature_telnyx: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens_telnyx: int | None = Field(None, ge=1, le=4096)

    # Voice Configuration
    voice_name_telnyx: str | None = Field(None, max_length=100)
    voice_style_telnyx: str | None = Field(None, max_length=50)
    voice_speed_telnyx: float | None = Field(None, ge=0.5, le=2.0)
    voice_pacing_ms_telnyx: int | None = Field(None, ge=0, le=2000)
    voice_sensitivity_telnyx: int | None = Field(None, ge=1000, le=10000)

    # STT Configuration
    stt_provider_telnyx: str | None = Field(None, max_length=50)
    stt_language_telnyx: str | None = Field(None, max_length=10)
    input_min_characters_telnyx: int | None = Field(None, ge=1, le=100)

    # Audio Processing
    enable_denoising_telnyx: bool | None = None
    enable_krisp_telnyx: bool | None = None
    enable_vad_telnyx: bool | None = None
    silence_timeout_ms_telnyx: int | None = Field(None, ge=500, le=5000)
    interruption_threshold_telnyx: int | None = Field(None, ge=0, le=20)

    # Messages
    first_message_telnyx: str | None = Field(None, max_length=500)
    first_message_mode_telnyx: str | None = Field(None, max_length=50)
    idle_message_telnyx: str | None = Field(None, max_length=500)

    # Behavior
    idle_timeout_telnyx: float | None = Field(None, ge=5.0, le=120.0)
    max_duration_telnyx: int | None = Field(None, ge=60, le=3600)
    initial_silence_timeout_ms_telnyx: int | None = Field(None, ge=1000, le=60000)

    # Recording & AMD
    enable_recording_telnyx: bool | None = None
    amd_config_telnyx: str | None = Field(None, max_length=50)

    # Advanced
    hallucination_blacklist_telnyx: str | None = Field(None, max_length=500)

    class Config:
        extra = "ignore"


class CoreConfigUpdate(BaseModel):
    """
    Core/Global configuration.

    Provider selection and extraction model.
    """
    stt_provider: str | None = Field(None, max_length=50)
    llm_provider: str | None = Field(None, max_length=50)
    tts_provider: str | None = Field(None, max_length=50)
    extraction_model: str | None = Field(None, max_length=100)

    class Config:
        extra = "ignore"
