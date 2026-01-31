"""
Browser/Simulator Profile Configuration Schema

Isolated schema for Browser profile following Hexagonal Architecture.
NO cross-contamination with Phone or Telnyx profiles.
"""

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
    context_window: int | None = Field(default=10, ge=1, le=50, alias="contextWindow")
    frequency_penalty: float | None = Field(default=0.0, ge=-2.0, le=2.0, alias="frequencyPenalty")
    presence_penalty: float | None = Field(default=0.0, ge=-2.0, le=2.0, alias="presencePenalty")
    tool_choice: str | None = Field(default="auto", alias="toolChoice")
    dynamic_vars_enabled: bool | None = Field(default=False, alias="dynamicVarsEnabled")
    dynamic_vars: dict | None = Field(default=None, alias="dynamicVars")

    # Advanced Call Features (AMD - Answering Machine Detection)
    voicemail_detection_enabled: bool | None = Field(
        default=False,
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

    # Features
    enable_denoising: bool | None = Field(None, alias="denoise")
    enable_end_call: bool | None = Field(None, alias="enableEndCall")
    enable_dial_keypad: bool | None = Field(None, alias="enableDialKeypad")
    transfer_phone_number: str | None = Field(None, alias="transferNum")

    model_config = {"extra": "ignore", "populate_by_name": True}
