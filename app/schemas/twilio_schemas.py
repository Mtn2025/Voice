"""
Twilio/Phone Profile Configuration Schema

Isolated schema for Twilio/Phone profile following Hexagonal Architecture.
All fields suffixed with _phone for database isolation.
NO cross-contamination with Browser or Telnyx profiles.
"""

from typing import Any

from pydantic import BaseModel, Field


class TwilioConfigUpdate(BaseModel):
    """
    Twilio/Phone profile configuration.
    """
    # LLM Configuration
    system_prompt: str | None = Field(None, max_length=10000, alias="prompt")
    llm_provider: str | None = Field(None, max_length=50, alias="provider")
    llm_model: str | None = Field(None, max_length=100, alias="model")
    temperature: float | None = Field(None, ge=0.0, le=2.0, alias="temp")
    max_tokens: int | None = Field(None, ge=1, le=4096, alias="tokens")

    # Voice Configuration
    # Voice Configuration
    tts_provider: str | None = Field(None, max_length=50, alias="voiceProvider")
    voice_name: str | None = Field(None, max_length=100, alias="voiceId")
    voice_style: str | None = Field(None, max_length=50, alias="voiceStyle")
    voice_speed: float | None = Field(None, ge=0.5, le=2.0, alias="voiceSpeed")
    voice_pacing_ms: int | None = Field(None, ge=0, le=2000, alias="voicePacing")
    voice_language: str | None = Field(None, alias="voiceLang")
    voice_pitch: int | None = Field(None, alias="voicePitch")
    voice_volume: int | None = Field(None, alias="voiceVolume")
    voice_style_degree: float | None = Field(None, alias="voiceStyleDegree")
    background_sound: str | None = Field(None, alias="voiceBgSound")

    # Advanced TTS (Phone)
    # Advanced TTS (Phone)
    voice_stability: float | None = Field(None, alias="voiceStability")
    voice_similarity_boost: float | None = Field(None, alias="voiceSimilarityBoost")
    voice_style_exaggeration: float | None = Field(None, alias="voiceStyleExaggeration")
    voice_speaker_boost: bool | None = Field(None, alias="voiceSpeakerBoost")
    voice_multilingual: bool | None = Field(None, alias="voiceMultilingual")
    tts_latency_optimization: int | None = Field(None, alias="ttsLatencyOptimization")
    tts_output_format: str | None = Field(None, alias="ttsOutputFormat")
    voice_filler_injection: bool | None = Field(None, alias="voiceFillerInjection")
    voice_backchanneling: bool | None = Field(None, alias="voiceBackchanneling")
    text_normalization_rule: str | None = Field(None, alias="textNormalizationRule")

    # STT Configuration
    stt_provider: str | None = Field(None, max_length=50, alias="sttProvider")
    stt_language: str | None = Field(None, max_length=10, alias="sttLang")
    input_min_characters: int | None = Field(None, ge=1, le=100, alias="inputMin")
    
    # Missing STT Fields
    stt_smart_formatting: bool | None = Field(None, alias="sttSmartFormatting")
    stt_punctuation: bool | None = Field(None, alias="punctuation")
    stt_profanity_filter: bool | None = Field(None, alias="profanityFilter")

    # Audio Processing
    enable_denoising: bool | None = Field(None, alias="denoise")
    interruption_threshold: int | None = Field(None, ge=0, le=20, alias="interruptWords")
    silence_timeout_ms: int | None = Field(None, alias="silence")

    # Messages
    first_message: str | None = Field(None, max_length=500, alias="msg")
    first_message_mode: str | None = Field(None, max_length=50, alias="mode")

    # Twilio-Specific
    twilio_account_sid: str | None = Field(None, alias="twilioAccountSid")
    twilio_auth_token: str | None = Field(None, alias="twilioAuthToken")
    twilio_from_number: str | None = Field(None, alias="twilioFromNumber")

    # SIP Trunk (Phone)
    sip_trunk_uri: str | None = Field(None, alias="sipTrunkUri")
    sip_auth_user: str | None = Field(None, alias="sipAuthUser")
    sip_auth_pass: str | None = Field(None, alias="sipAuthPass")
    fallback_number: str | None = Field(None, alias="fallbackNumber")
    geo_region: str | None = Field(None, alias="geoRegion")
    caller_id: str | None = Field(None, alias="callerIdPhone")

    # Recording & Compliance (Phone)
    recording_channels: str | None = Field(None, alias="recordingChannels")
    hipaa_enabled: bool | None = Field(None, alias="hipaaEnabled")
    dtmf_listening_enabled: bool | None = Field(None, alias="dtmfListeningEnabled")

    # Tools Configuration
    tools_schema: dict[str, Any] | None = Field(None, alias="toolsSchema")
    async_tools: bool | None = Field(None, alias="asyncTools")
    client_tools_enabled: bool | None = Field(None, alias="clientToolsEnabled")
    tool_server_url: str | None = Field(None, alias="toolServerUrl")
    tool_server_secret: str | None = Field(None, alias="toolServerSecret")

    # Global Integrations & System (Mapped via Whitelist)
    crm_enabled: bool | None = Field(None, alias="crmEnabled")
    webhook_url: str | None = Field(None, alias="webhookUrl")
    concurrency_limit: int | None = Field(None, alias="concurrencyLimit")
    spend_limit_daily: float | None = Field(None, alias="spendLimitDaily")

    # Advanced
    hallucination_blacklist: str | None = Field(None, max_length=500, alias="blacklist")

    # Conversation Style
    response_length: str | None = Field(None, alias="responseLength")
    conversation_tone: str | None = Field(None, alias="conversationTone")
    conversation_formality: str | None = Field(None, alias="conversationFormality")
    conversation_pacing: str | None = Field(None, alias="conversationPacing")
    
    # Advanced LLM Controls (Phone)
    context_window: int | None = Field(None, alias="contextWindow")
    frequency_penalty: float | None = Field(None, alias="frequencyPenalty")
    presence_penalty: float | None = Field(None, alias="presencePenalty")
    tool_choice: str | None = Field(None, alias="toolChoice")
    dynamic_vars_enabled: bool | None = Field(None, alias="dynamicVarsEnabled")
    dynamic_vars: str | None = Field(None, alias="dynamicVars")

    # Twilio Recording & Machine Detection
    twilio_machine_detection: str | None = Field(
        default="Enable",
        alias="twilioMachineDetection",
        description="Twilio answering machine detection setting"
    )
    twilio_record: bool | None = Field(
        default=False,
        alias="twilioRecord",
        description="Enable call recording in Twilio"
    )
    twilio_recording_channels: str | None = Field(
        default="dual",
        alias="twilioRecordingChannels",
        description="Recording channels: mono or dual"
    )
    twilio_trim_silence: bool | None = Field(
        default=True,
        alias="twilioTrimSilence",
        description="Trim silence from recordings"
    )

    # Advanced Call Features (AMD)
    voicemail_detection_enabled: bool | None = Field(
        default=True,
        alias="voicemailDetectionEnabled",
        description="Enable answering machine detection"
    )
    voicemail_message: str | None = Field(
        default="Hola, llamaba de Ubrokers. Le enviaré un WhatsApp.",
        alias="voicemailMessage",
        description="Message to leave on voicemail"
    )
    machine_detection_sensitivity: float | None = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        alias="machineDetectionSensitivity",
        description="Sensitivity for machine detection (0-1)"
    )

    model_config = {"extra": "ignore", "populate_by_name": True}
