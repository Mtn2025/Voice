"""
Configuration Schemas for Dashboard

Pydantic schemas for validating configuration updates by profile.
Replaces monolithic Form endpoint with type-safe, modular schemas.
"""



from typing import Any
from pydantic import BaseModel, Field



class BrowserConfigUpdate(BaseModel):
    """
    Browser/Simulator profile configuration.
    All fields are optional (partial update with PATCH).
    """
    # LLM Configuration
    system_prompt: str | None = Field(None, max_length=10000, alias="prompt")
    temperature: float | None = Field(None, ge=0.0, le=2.0, alias="temp")
    llm_model: str | None = Field(None, max_length=100, alias="model")
    llm_provider: str | None = Field(None, max_length=50, alias="provider")
    max_tokens: int | None = Field(None, ge=1, le=4096, alias="tokens")

    # Voice Configuration
    tts_provider: str | None = Field(None, max_length=50, alias="voiceProvider")
    voice_name: str | None = Field(None, max_length=100, alias="voiceId")
    voice_style: str | None = Field(None, max_length=50, alias="voiceStyle")
    voice_speed: float | None = Field(None, ge=0.5, le=2.0, alias="voiceSpeed")
    voice_pacing_ms: int | None = Field(None, ge=0, le=2000, alias="voicePacing")
    voice_pitch: int | None = Field(None, alias="voicePitch")
    voice_volume: int | None = Field(None, alias="voiceVolume")
    voice_style_degree: float | None = Field(None, alias="voiceStyleDegree")
    voice_language: str | None = Field(None, alias="voiceLang")

    # Advanced TTS (Browser)
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
    stt_language: str | None = Field(None, max_length=10, alias="sttLang")
    stt_provider: str | None = Field(None, max_length=50, alias="sttProvider")

    # Behavior
    background_sound: str | None = Field(None, max_length=50, alias="voiceBgSound")
    background_sound_url: str | None = Field(None, alias="voiceBgUrl")
    idle_timeout: float | None = Field(None, ge=5.0, le=120.0, alias="idleTimeout")
    idle_message: str | None = Field(None, max_length=500, alias="idleMessage")
    inactivity_max_retries: int | None = Field(None, ge=1, le=10, alias="maxRetries")
    max_duration: int | None = Field(None, ge=60, le=3600, alias="maxDuration")
    interruption_threshold: int | None = Field(None, ge=0, le=20, alias="interruptWords")
    silence_timeout_ms: int | None = Field(None, alias="silence")

    # Messages
    first_message: str | None = Field(None, max_length=500, alias="msg")
    first_message_mode: str | None = Field(None, max_length=50, alias="mode")

    # Advanced
    hallucination_blacklist: str | None = Field(None, max_length=500, alias="blacklist")

    # Conversation Style
    response_length: str | None = Field(None, alias="responseLength")
    conversation_tone: str | None = Field(None, alias="conversationTone")
    conversation_formality: str | None = Field(None, alias="conversationFormality")
    conversation_pacing: str | None = Field(None, alias="conversationPacing")

    # Advanced LLM Controls
    context_window: int | None = Field(None, alias="contextWindow")
    frequency_penalty: float | None = Field(None, alias="frequencyPenalty")
    presence_penalty: float | None = Field(None, alias="presencePenalty")
    tool_choice: str | None = Field(None, alias="toolChoice")
    dynamic_vars_enabled: bool | None = Field(None, alias="dynamicVarsEnabled")
    dynamic_vars: str | None = Field(None, alias="dynamicVars")

    # Features
    enable_denoising: bool | None = Field(None, alias="denoise")
    enable_end_call: bool | None = Field(None, alias="enableEndCall")
    enable_dial_keypad: bool | None = Field(None, alias="enableDialKeypad")
    transfer_phone_number: str | None = Field(None, alias="transferNum")

    model_config = {"extra": "ignore", "populate_by_name": True}


class TwilioConfigUpdate(BaseModel):
    """
    Twilio/Phone profile configuration.
    """
    # LLM Configuration
    system_prompt_phone: str | None = Field(None, max_length=10000, alias="prompt")
    llm_provider_phone: str | None = Field(None, max_length=50, alias="provider")
    llm_model_phone: str | None = Field(None, max_length=100, alias="model")
    temperature_phone: float | None = Field(None, ge=0.0, le=2.0, alias="temp")
    max_tokens_phone: int | None = Field(None, ge=1, le=4096, alias="tokens")

    # Voice Configuration
    tts_provider_phone: str | None = Field(None, max_length=50, alias="voiceProvider")
    voice_name_phone: str | None = Field(None, max_length=100, alias="voiceId")
    voice_style_phone: str | None = Field(None, max_length=50, alias="voiceStyle")
    voice_speed_phone: float | None = Field(None, ge=0.5, le=2.0, alias="voiceSpeed")
    voice_pacing_ms_phone: int | None = Field(None, ge=0, le=2000, alias="voicePacing")
    voice_language_phone: str | None = Field(None, alias="voiceLang")
    voice_pitch_phone: int | None = Field(None, alias="voicePitch")
    voice_volume_phone: int | None = Field(None, alias="voiceVolume")
    voice_style_degree_phone: float | None = Field(None, alias="voiceStyleDegree")
    background_sound_phone: str | None = Field(None, alias="voiceBgSound")

    # Advanced TTS (Phone)
    voice_stability_phone: float | None = Field(None, alias="voiceStability")
    voice_similarity_boost_phone: float | None = Field(None, alias="voiceSimilarityBoost")
    voice_style_exaggeration_phone: float | None = Field(None, alias="voiceStyleExaggeration")
    voice_speaker_boost_phone: bool | None = Field(None, alias="voiceSpeakerBoost")
    voice_multilingual_phone: bool | None = Field(None, alias="voiceMultilingual")
    tts_latency_optimization_phone: int | None = Field(None, alias="ttsLatencyOptimization")
    tts_output_format_phone: str | None = Field(None, alias="ttsOutputFormat")
    voice_filler_injection_phone: bool | None = Field(None, alias="voiceFillerInjection")
    voice_backchanneling_phone: bool | None = Field(None, alias="voiceBackchanneling")
    text_normalization_rule_phone: str | None = Field(None, alias="textNormalizationRule")

    # STT Configuration
    stt_provider_phone: str | None = Field(None, max_length=50, alias="sttProvider")
    stt_language_phone: str | None = Field(None, max_length=10, alias="sttLang")
    input_min_characters_phone: int | None = Field(None, ge=1, le=100, alias="inputMin")

    # Audio Processing
    enable_denoising_phone: bool | None = Field(None, alias="denoise")
    interruption_threshold_phone: int | None = Field(None, ge=0, le=20, alias="interruptWords")
    silence_timeout_ms_phone: int | None = Field(None, alias="silence")

    # Messages
    first_message_phone: str | None = Field(None, max_length=500, alias="msg")
    first_message_mode_phone: str | None = Field(None, max_length=50, alias="mode")

    # Twilio-Specific
    twilio_account_sid: str | None = Field(None, alias="twilioAccountSid")
    twilio_auth_token: str | None = Field(None, alias="twilioAuthToken")
    twilio_from_number: str | None = Field(None, alias="twilioFromNumber")

    # Tools Configuration
    tools_schema: dict[str, Any] | None = Field(None, alias="toolsSchema")
    async_tools: bool | None = Field(None, alias="asyncTools")
    client_tools_enabled: bool | None = Field(None, alias="clientToolsEnabled")

    # Advanced
    hallucination_blacklist_phone: str | None = Field(None, max_length=500, alias="blacklist")

    # Conversation Style
    response_length_phone: str | None = Field(None, alias="responseLength")
    conversation_tone_phone: str | None = Field(None, alias="conversationTone")
    conversation_formality_phone: str | None = Field(None, alias="conversationFormality")
    conversation_pacing_phone: str | None = Field(None, alias="conversationPacing")

    # Advanced LLM Controls (Phone)
    context_window_phone: int | None = Field(None, alias="contextWindow")
    frequency_penalty_phone: float | None = Field(None, alias="frequencyPenalty")
    presence_penalty_phone: float | None = Field(None, alias="presencePenalty")
    tool_choice_phone: str | None = Field(None, alias="toolChoice")
    dynamic_vars_enabled_phone: bool | None = Field(None, alias="dynamicVarsEnabled")
    dynamic_vars_phone: str | None = Field(None, alias="dynamicVars")

    model_config = {"extra": "ignore", "populate_by_name": True}


class TelnyxConfigUpdate(BaseModel):
    """
    Telnyx profile configuration (100% isolated from Twilio/Phone).
    All fields are suffixed with _telnyx for database isolation.
    """
    # LLM Configuration
    system_prompt_telnyx: str | None = Field(None, max_length=10000, alias="prompt")
    llm_provider_telnyx: str | None = Field(None, max_length=50, alias="provider")
    llm_model_telnyx: str | None = Field(None, max_length=100, alias="model")
    temperature_telnyx: float | None = Field(None, ge=0.0, le=2.0, alias="temp")
    max_tokens_telnyx: int | None = Field(None, ge=1, le=4096, alias="tokens")

    # Voice Configuration
    tts_provider_telnyx: str | None = Field(None, max_length=50, alias="voiceProvider")
    voice_name_telnyx: str | None = Field(None, max_length=100, alias="voiceId")
    voice_style_telnyx: str | None = Field(None, max_length=50, alias="voiceStyle")
    voice_speed_telnyx: float | None = Field(None, ge=0.5, le=2.0, alias="voiceSpeed")
    voice_pacing_ms_telnyx: int | None = Field(None, ge=0, le=2000, alias="voicePacing")
    voice_language_telnyx: str | None = Field(None, alias="voiceLang")
    voice_pitch_telnyx: int | None = Field(None, alias="voicePitch")
    voice_volume_telnyx: int | None = Field(None, alias="voiceVolume")
    voice_style_degree_telnyx: float | None = Field(None, alias="voiceStyleDegree")
    background_sound_telnyx: str | None = Field(None, alias="voiceBgSound")
    background_sound_url_telnyx: str | None = Field(None, alias="voiceBgUrl")

    # Advanced TTS (Telnyx)
    voice_stability_telnyx: float | None = Field(None, alias="voiceStability")
    voice_similarity_boost_telnyx: float | None = Field(None, alias="voiceSimilarityBoost")
    voice_style_exaggeration_telnyx: float | None = Field(None, alias="voiceStyleExaggeration")
    voice_speaker_boost_telnyx: bool | None = Field(None, alias="voiceSpeakerBoost")
    voice_multilingual_telnyx: bool | None = Field(None, alias="voiceMultilingual")
    tts_latency_optimization_telnyx: int | None = Field(None, alias="ttsLatencyOptimization")
    tts_output_format_telnyx: str | None = Field(None, alias="ttsOutputFormat")
    voice_filler_injection_telnyx: bool | None = Field(None, alias="voiceFillerInjection")
    voice_backchanneling_telnyx: bool | None = Field(None, alias="voiceBackchanneling")
    text_normalization_rule_telnyx: str | None = Field(None, alias="textNormalizationRule")

    # Telnyx Advanced Audio
    audio_codec_telnyx: str | None = Field(None, alias="audioCodec")
    noise_suppression_level_telnyx: str | None = Field(None, alias="noiseSuppressionLevel")
    enable_backchannel_telnyx: bool | None = Field(None, alias="enableBackchannel")

    # STT Configuration
    stt_provider_telnyx: str | None = Field(None, max_length=50, alias="sttProvider")
    stt_language_telnyx: str | None = Field(None, max_length=10, alias="sttLang")
    input_min_characters_telnyx: int | None = Field(None, ge=1, le=100, alias="inputMin")

    # Audio Processing
    enable_denoising_telnyx: bool | None = Field(None, alias="denoise")
    enable_krisp_telnyx: bool | None = Field(None, alias="krisp")
    enable_vad_telnyx: bool | None = Field(None, alias="vad")
    silence_timeout_ms_telnyx: int | None = Field(None, ge=500, le=5000, alias="silence")
    interruption_threshold_telnyx: int | None = Field(None, ge=0, le=20, alias="interruptWords")
    voice_sensitivity_telnyx: int | None = Field(None, alias="interruptRMS")
    vad_threshold_telnyx: float | None = Field(None, alias="vadThreshold")

    # Messages
    first_message_telnyx: str | None = Field(None, max_length=500, alias="msg")
    first_message_mode_telnyx: str | None = Field(None, max_length=50, alias="mode")
    idle_message_telnyx: str | None = Field(None, max_length=500, alias="idleMessage")

    # Behavior
    idle_timeout_telnyx: float | None = Field(None, ge=5.0, le=120.0, alias="idleTimeout")
    max_duration_telnyx: int | None = Field(None, ge=60, le=3600, alias="maxDuration")

    # Advanced LLM Controls (Telnyx)
    context_window_telnyx: int | None = Field(None, alias="contextWindow")
    frequency_penalty_telnyx: float | None = Field(None, alias="frequencyPenalty")
    presence_penalty_telnyx: float | None = Field(None, alias="presencePenalty")
    tool_choice_telnyx: str | None = Field(None, alias="toolChoice")
    dynamic_vars_enabled_telnyx: bool | None = Field(None, alias="dynamicVarsEnabled")
    dynamic_vars_telnyx: str | None = Field(None, alias="dynamicVars")

    # Conversation Style (Telnyx)
    response_length_telnyx: str | None = Field(None, alias="responseLength")
    conversation_tone_telnyx: str | None = Field(None, alias="conversationTone")
    conversation_formality_telnyx: str | None = Field(None, alias="conversationFormality")
    conversation_pacing_telnyx: str | None = Field(None, alias="conversationPacing")

    # System & Safety (Telnyx-specific limits - auditoría isolation)
    max_retries_telnyx: int | None = Field(None, alias="maxRetries")
    concurrency_limit_telnyx: int | None = Field(None, alias="concurrencyLimit")
    daily_spend_limit_telnyx: float | None = Field(None, alias="dailySpendLimit")
    environment_tag_telnyx: str | None = Field(None, alias="environmentTag")
    privacy_mode_telnyx: bool | None = Field(None, alias="privacyMode")
    audit_log_enabled_telnyx: bool | None = Field(None, alias="auditLogEnabled")

    # Recording & AMD
    enable_recording_telnyx: bool | None = Field(None, alias="enableRecording")
    amd_config_telnyx: str | None = Field(None, max_length=50, alias="amdConfig")

    # Advanced
    hallucination_blacklist_telnyx: str | None = Field(None, max_length=500, alias="blacklist")

    # Telnyx Connectivity (Ghost UI fix - auditoría Tab 6)
    telnyx_api_key: str | None = Field(None, alias="telnyxApiKey")
    telnyx_connection_id: str | None = Field(None, alias="telnyxConnectionId")
    sip_trunk_uri_telnyx: str | None = Field(None, alias="sipTrunkUri")
    sip_auth_user_telnyx: str | None = Field(None, alias="sipAuthUser")
    sip_auth_pass_telnyx: str | None = Field(None, alias="sipAuthPass")
    caller_id_telnyx: str | None = Field(None, alias="callerIdTelnyx")
    fallback_number_telnyx: str | None = Field(None, alias="fallbackNumber")
    geo_region_telnyx: str | None = Field(None, alias="geoRegion")

    # Tools Configuration
    tools_schema_telnyx: dict[str, Any] | None = Field(None, alias="toolsSchema")
    async_tools_telnyx: bool | None = Field(None, alias="asyncTools")
    client_tools_enabled_telnyx: bool | None = Field(None, alias="clientToolsEnabled")
    
    # Tool Server Config (Telnyx)
    tool_server_url_telnyx: str | None = Field(None, alias="toolServerUrl")
    tool_server_secret_telnyx: str | None = Field(None, alias="toolServerSecret")
    tool_timeout_ms_telnyx: int | None = Field(None, alias="toolTimeoutMs")
    tool_retry_count_telnyx: int | None = Field(None, alias="toolRetryCount")
    tool_error_msg_telnyx: str | None = Field(None, alias="toolErrorMsg")

    # Integrations (Webhook/CRM Telnyx)
    webhook_url_telnyx: str | None = Field(None, alias="webhookUrl")
    webhook_secret_telnyx: str | None = Field(None, alias="webhookSecret")
    crm_enabled_telnyx: bool | None = Field(None, alias="crmEnabled")
    baserow_token_telnyx: str | None = Field(None, alias="baserowToken")
    baserow_table_id_telnyx: int | None = Field(None, alias="baserowTableId")

    model_config = {"extra": "ignore", "populate_by_name": True}


class CoreConfigUpdate(BaseModel):
    """
    Core/Global configuration.
    """
    stt_provider: str | None = Field(None, max_length=50, alias="sttProvider")
    llm_provider: str | None = Field(None, max_length=50, alias="llmProvider")
    tts_provider: str | None = Field(None, max_length=50, alias="voiceProvider")
    extraction_model: str | None = Field(None, max_length=100, alias="extractionModel")

    model_config = {"extra": "ignore", "populate_by_name": True}
