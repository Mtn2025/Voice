"""
Profile Configuration Schema

Type-safe Pydantic schema for agent profile configurations.
Eliminates redundant column access patterns (_phone, _telnyx suffixes).

This schema represents configuration for a SINGLE profile (browser, twilio, or telnyx).
The AgentConfig model has 3x these fields with suffixes.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProfileConfigSchema(BaseModel):
    """
    Type-safe profile configuration (browser, twilio, telnyx).

    All fields are optional to support partial updates.
    Defaults match AgentConfig column defaults.
    """

    # =============================================================================
    # STT (Speech-To-Text) Configuration
    # =============================================================================

    stt_provider: str | None = Field(None, description="STT provider (azure, deepgram, google)")
    stt_language: str | None = Field(None, description="Language code (e.g., es-MX, en-US)")
    stt_model: str | None = Field(None, description="STT model name")
    stt_keywords: list[str] | None = Field(None, description="Boost keywords for recognition")
    stt_silence_timeout: int | None = Field(None, ge=100, le=5000, description="Silence timeout in ms")
    stt_utterance_end_strategy: str | None = Field(None, description="Utterance end detection strategy")

    # STT Formatting & Filters
    stt_punctuation: bool | None = Field(None, description="Enable automatic punctuation")
    stt_profanity_filter: bool | None = Field(None, description="Filter profanity")
    stt_smart_formatting: bool | None = Field(None, description="Smart formatting (numbers, dates)")

    # STT Advanced Features
    stt_diarization: bool | None = Field(None, description="Speaker diarization")
    stt_multilingual: bool | None = Field(None, description="Multilingual detection")

    # =============================================================================
    # LLM (Language Model) Configuration
    # =============================================================================

    llm_provider: str | None = Field(None, description="LLM provider (groq, openai, anthropic)")
    llm_model: str | None = Field(None, description="Model name")
    system_prompt: str | None = Field(None, description="System prompt for LLM")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="LLM temperature")

    # Advanced LLM Controls
    context_window: int | None = Field(None, ge=1, le=50, description="Conversation context window")
    frequency_penalty: float | None = Field(None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float | None = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    tool_choice: str | None = Field(None, description="Tool choice strategy (auto, required, none)")
    dynamic_vars_enabled: bool | None = Field(None, description="Enable dynamic variables")
    dynamic_vars: dict[str, Any] | None = Field(None, description="Dynamic context variables")

    # =============================================================================
    # TTS (Text-To-Speech) Configuration
    # =============================================================================

    tts_provider: str | None = Field(None, description="TTS provider (azure, elevenlabs, google)")
    voice_name: str | None = Field(None, description="Voice name/ID")
    voice_language: str | None = Field(None, description="Voice language code")
    voice_style: str | None = Field(None, description="Voice style (e.g., friendly, cheerful)")
    voice_speed: float | None = Field(None, ge=0.5, le=2.0, description="Voice speed multiplier")

    # Voice Expression Controls (Azure TTS SSML)
    voice_pitch: int | None = Field(None, ge=-50, le=50, description="Voice pitch adjustment")
    voice_volume: int | None = Field(None, ge=0, le=200, description="Voice volume (0-200)")
    voice_style_degree: float | None = Field(None, ge=0.01, le=2.0, description="Style intensity")

    # ElevenLabs Specifics
    voice_stability: float | None = Field(None, ge=0.0, le=1.0, description="Voice stability (ElevenLabs)")
    voice_similarity_boost: float | None = Field(None, ge=0.0, le=1.0, description="Similarity boost (ElevenLabs)")
    voice_style_exaggeration: float | None = Field(None, ge=0.0, le=1.0, description="Style exaggeration (ElevenLabs)")
    voice_speaker_boost: bool | None = Field(None, description="Speaker boost (ElevenLabs)")
    voice_multilingual: bool | None = Field(None, description="Multilingual mode (ElevenLabs)")

    # Technical Settings
    tts_latency_optimization: int | None = Field(None, ge=0, le=4, description="Latency optimization level")
    tts_output_format: str | None = Field(None, description="Audio output format (pcm_16000, pcm_8000)")

    # Humanization
    voice_filler_injection: bool | None = Field(None, description="Inject filler words (um, ah)")
    voice_backchanneling: bool | None = Field(None, description="Enable backchanneling")
    text_normalization_rule: str | None = Field(None, description="Text normalization strategy")
    pronunciation_dictionary: dict[str, str] | None = Field(None, description="Custom pronunciations")

    # =============================================================================
    # Flow Control
    # =============================================================================

    idle_timeout: float | None = Field(None, ge=5.0, le=60.0, description="Idle timeout in seconds")
    idle_message: str | None = Field(None, description="Message on idle timeout")
    inactivity_max_retries: int | None = Field(None, ge=0, le=10, description="Max retries before hangup")
    max_duration: int | None = Field(None, ge=60, le=3600, description="Max call duration in seconds")

    first_message: str | None = Field(None, description="First message to speak")
    first_message_mode: str | None = Field(None, description="speak-first or wait-for-greeting")
    max_tokens: int | None = Field(None, ge=50, le=1000, description="Max tokens per response")

    # =============================================================================
    # Conversation Style
    # =============================================================================

    response_length: str | None = Field(None, description="Response length (short, medium, long)")
    conversation_tone: str | None = Field(None, description="Conversation tone (warm, neutral, professional)")
    conversation_formality: str | None = Field(None, description="Formality level (casual, semi_formal, formal)")
    conversation_pacing: str | None = Field(None, description="Pacing (slow, moderate, fast)")

    # =============================================================================
    # Interruption Handling
    # =============================================================================

    barge_in_enabled: bool | None = Field(None, description="Allow user interruptions")
    interruption_threshold: int | None = Field(None, ge=1, le=10, description="Noise tolerance for interruptions")
    interruption_sensitivity: float | None = Field(None, ge=0.0, le=1.0, description="Interruption detection sensitivity")
    interruption_phrases: list[str] | None = Field(None, description="Custom interruption trigger phrases")

    # =============================================================================
    # Voice Activity Detection (VAD)
    # =============================================================================

    voice_sensitivity: int | None = Field(None, ge=100, le=10000, description="Microphone sensitivity")
    vad_threshold: float | None = Field(None, ge=0.0, le=1.0, description="Silero VAD threshold")
    silence_timeout_ms: int | None = Field(None, ge=100, le=5000, description="Silence timeout in ms")
    initial_silence_timeout_ms: int | None = Field(None, ge=5000, le=60000, description="Initial silence timeout")

    # =============================================================================
    # Machine Detection
    # =============================================================================

    voicemail_detection_enabled: bool | None = Field(None, description="Enable voicemail detection")
    voicemail_message: str | None = Field(None, description="Message to leave on voicemail")
    machine_detection_sensitivity: float | None = Field(None, ge=0.0, le=1.0, description="AMD sensitivity")

    # =============================================================================
    # Pacing & Naturalness
    # =============================================================================

    response_delay_seconds: float | None = Field(None, ge=0.0, le=3.0, description="Delay before responding")
    wait_for_greeting: bool | None = Field(None, description="Wait for user greeting")
    hyphenation_enabled: bool | None = Field(None, description="Enable word hyphenation")
    end_call_phrases: list[str] | None = Field(None, description="Phrases that trigger call end")

    # =============================================================================
    # Audio Processing
    # =============================================================================

    background_sound: str | None = Field(None, description="Background sound type (none, office, cafe)")
    background_sound_url: str | None = Field(None, description="Custom background sound URL")
    enable_denoising: bool | None = Field(None, description="Enable noise reduction")
    input_min_characters: int | None = Field(None, ge=1, le=50, description="Min characters before processing")
    voice_pacing_ms: int | None = Field(None, ge=0, le=2000, description="Pacing delay in ms")
    hallucination_blacklist: str | None = Field(None, description="Comma-separated hallucination patterns")

    # Advanced VAD/Silence
    initial_silence_timeout_ms: int | None = Field(None, ge=1000, le=60000, description="Initial silence timeout")

    # =============================================================================
    # Telephony-Specific (Telnyx/Twilio) & Connectivity (PHASE V)
    # =============================================================================

    # Credentials (BYOC)
    twilio_account_sid: str | None = Field(None, description="Twilio Account SID")
    twilio_auth_token: str | None = Field(None, description="Twilio Auth Token")
    twilio_from_number: str | None = Field(None, description="Twilio From Number")
    telnyx_api_key: str | None = Field(None, description="Telnyx API Key")
    telnyx_connection_id: str | None = Field(None, description="Telnyx Connection ID")

    # SIP & Infrastructure
    caller_id_phone: str | None = Field(None, description="Twilio/Phone Caller ID")
    sip_trunk_uri_phone: str | None = Field(None, description="Twilio SIP Trunk URI")
    sip_auth_user_phone: str | None = Field(None, description="Twilio SIP User")
    sip_auth_pass_phone: str | None = Field(None, description="Twilio SIP Password")
    fallback_number_phone: str | None = Field(None, description="Twilio Fallback Number")
    geo_region_phone: str | None = Field(None, description="Twilio Geo Region")

    caller_id_telnyx: str | None = Field(None, description="Telnyx Caller ID")
    sip_trunk_uri_telnyx: str | None = Field(None, description="Telnyx SIP Trunk URI")
    sip_auth_user_telnyx: str | None = Field(None, description="Telnyx SIP User")
    sip_auth_pass_telnyx: str | None = Field(None, description="Telnyx SIP Password")
    fallback_number_telnyx: str | None = Field(None, description="Telnyx Fallback Number")
    geo_region_telnyx: str | None = Field(None, description="Telnyx Geo Region")

    # Recording & Compliance Extensions
    recording_channels_phone: str | None = Field(None, description="Twilio Recording Channels")
    recording_enabled_phone: bool | None = Field(None, description="Twilio Recording Enabled")
    recording_channels_telnyx: str | None = Field(None, description="Telnyx Recording Channels")

    hipaa_enabled_phone: bool | None = Field(None, description="Twilio HIPAA Mode")
    hipaa_enabled_telnyx: bool | None = Field(None, description="Telnyx HIPAA Mode")

    dtmf_listening_enabled_phone: bool | None = Field(None, description="Twilio DTMF Listening")
    dtmf_listening_enabled_telnyx: bool | None = Field(None, description="Telnyx DTMF Listening")

    # =============================================================================
    # System Limits & Governance (PHASE VIII)
    # =============================================================================
    concurrency_limit: int | None = Field(None, description="Max concurrent calls")
    spend_limit_daily: float | None = Field(None, description="Daily spend limit in USD")
    audit_log_enabled: bool | None = Field(None, description="Enable audit logging")

    enable_krisp_telnyx: bool | None = Field(None, description="Enable Krisp noise suppression (Telnyx)")
    noise_suppression_level: str | None = Field(None, description="Noise suppression level")
    enable_vad_telnyx: bool | None = Field(None, description="Enable VAD (Telnyx)")
    audio_codec: str | None = Field(None, description="Audio codec (PCMU, PCMA)")
    enable_backchannel: bool | None = Field(None, description="Enable backchannel")
    amd_config_telnyx: str | None = Field(None, description="AMD configuration (Telnyx)")
    enable_recording_telnyx: bool | None = Field(None, description="Enable call recording (Telnyx)")

    # Twilio-specific
    twilio_machine_detection: str | None = Field(None, description="Twilio AMD mode")
    twilio_record: bool | None = Field(None, description="Record call (Twilio)")
    twilio_recording_channels: str | None = Field(None, description="Recording channels (dual, mono)")
    twilio_trim_silence: bool | None = Field(None, description="Trim silence from recording")

    # =============================================================================
    # Analysis & Data
    # =============================================================================

    analysis_prompt: str | None = Field(None, description="Post-call analysis prompt")
    success_rubric: str | None = Field(None, description="Success criteria")
    extraction_schema: dict[str, Any] | None = Field(None, description="Data extraction schema")
    sentiment_analysis: bool | None = Field(None, description="Enable sentiment analysis")
    transcript_format: str | None = Field(None, description="Transcript format (text, json)")
    cost_tracking_enabled: bool | None = Field(None, description="Track API costs")

    # =============================================================================
    # Webhooks & Compliance
    # =============================================================================

    webhook_url: str | None = Field(None, description="Webhook URL for events")
    webhook_secret: str | None = Field(None, description="Webhook secret for validation")
    log_webhook_url: str | None = Field(None, description="Logging webhook URL")
    pii_redaction_enabled: bool | None = Field(None, description="Redact PII from logs")
    retention_days: int | None = Field(None, ge=1, le=365, description="Data retention in days")

    # =============================================================================
    # Function Calling (Tools)
    # =============================================================================

    # =============================================================================
    # Function Calling (Tools)
    # =============================================================================

    tool_server_url: str | None = Field(None, description="Tool server URL")
    tool_server_secret: str | None = Field(None, description="Tool server secret")
    tool_timeout_ms: int | None = Field(None, ge=1000, le=30000, description="Tool timeout in ms")
    tool_retry_count: int | None = Field(None, ge=0, description="Tool retry count")
    tool_error_msg: str | None = Field(None, description="Error message on tool failure")

    tools_schema: dict[str, Any] | None = Field(None, description="Tool definitions schema")
    async_tools: bool | None = Field(None, description="Enable async tool execution")
    client_tools_enabled: bool | None = Field(None, description="Enable client-side tools")

    redact_params: list[str] | None = Field(None, description="Parameters to redact from logs")
    state_injection_enabled: bool | None = Field(None, description="Allow state injection")
    transfer_whitelist: list[str] | None = Field(None, description="Whitelisted transfer numbers")

    # =============================================================================
    # System & DevOps
    # =============================================================================

    environment: str | None = Field(None, description="Environment (development, production)")
    privacy_mode: bool | None = Field(None, description="Privacy mode (no logging)")

    # =============================================================================
    # Validators
    # =============================================================================

    @field_validator('voice_speed')
    @classmethod
    def validate_voice_speed(cls, v: float | None) -> float | None:
        """Validate voice speed is within valid range."""
        if v is not None and (v < 0.5 or v > 2.0):
            raise ValueError('voice_speed must be between 0.5 and 2.0')
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: float | None) -> float | None:
        """Validate temperature is within valid range."""
        if v is not None and (v < 0.0 or v > 2.0):
            raise ValueError('temperature must be between 0.0 and 2.0')
        return v

    @field_validator('context_window')
    @classmethod
    def validate_context_window(cls, v: int | None) -> int | None:
        """Validate context window is reasonable."""
        if v is not None and (v < 1 or v > 50):
            raise ValueError('context_window must be between 1 and 50')
        return v

    @field_validator('vad_threshold')
    @classmethod
    def validate_vad_threshold(cls, v: float | None) -> float | None:
        """Validate VAD threshold."""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError('vad_threshold must be between 0.0 and 1.0')
        return v

    model_config = {
        "validate_assignment": True,
        "extra": "allow",  # Allow extra fields for forward compatibility
        "str_strip_whitespace": True,
    }
