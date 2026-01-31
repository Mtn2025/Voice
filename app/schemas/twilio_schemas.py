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

    # SIP Trunk (Phone)
    sip_trunk_uri_phone: str | None = Field(None, alias="sipTrunkUri")
    sip_auth_user_phone: str | None = Field(None, alias="sipAuthUser")
    sip_auth_pass_phone: str | None = Field(None, alias="sipAuthPass")
    fallback_number_phone: str | None = Field(None, alias="fallbackNumber")
    geo_region_phone: str | None = Field(None, alias="geoRegion")
    caller_id_phone: str | None = Field(None, alias="callerIdPhone")

    # Recording & Compliance (Phone)
    recording_channels_phone: str | None = Field(None, alias="recordingChannels")
    hipaa_enabled_phone: bool | None = Field(None, alias="hipaaEnabled")
    dtmf_listening_enabled_phone: bool | None = Field(None, alias="dtmfListeningEnabled")

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
