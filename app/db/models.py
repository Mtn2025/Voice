from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship

if TYPE_CHECKING:
    from app.schemas.profile_config import ProfileConfigSchema


class Base(DeclarativeBase):
    pass


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    client_type = Column(String, default="simulator")  # simulator, twilio, telnyx
    extracted_data = Column(JSON, nullable=True)

    transcripts = relationship("Transcript", back_populates="call")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), index=True)
    role = Column(String)  # user or assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="transcripts")


class AgentConfig(Base):
    """
    Agent Configuration.
    Denormalized table storing independent profiles for Browser, Twilio, and Telnyx interactions.
    """
    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, default="default")

    # Providers
    stt_provider = Column(String, default="azure")
    stt_language = Column(String, default="es-MX")
    llm_provider = Column(String, default="groq")
    llm_model = Column(String, default="llama-3.3-70b-versatile")
    extraction_model = Column(String, default="llama-3.1-8b-instant")
    interruption_threshold = Column(Integer, default=5)  # Noise Tolerance (Browser)
    interruption_threshold_phone = Column(Integer, default=2)  # Noise Tolerance (Phone)
    tts_provider = Column(String, default="azure")

    # =============================================================================
    # STT ADVANCED FEATURES (Internal - Backend Only)
    # Used in: app/adapters/outbound/stt/azure_stt_adapter.py
    #          app/adapters/outbound/stt/deepgram_stt_adapter.py
    # Purpose: Advanced configuration for Speech-to-Text providers (Deepgram/Azure)
    # Note: Not exposed in UI schemas, configured programmatically per provider
    # =============================================================================
    # STT Advanced
    stt_model = Column(String, default="nova-2")
    stt_keywords = Column(JSON, nullable=True)
    stt_silence_timeout = Column(Integer, default=500)
    stt_utterance_end_strategy = Column(String, default="default")

    # STT Formatting & Filters
    stt_punctuation = Column(Boolean, default=True)
    stt_profanity_filter = Column(Boolean, default=True)
    stt_smart_formatting = Column(Boolean, default=True)

    # STT Advanced Features
    stt_diarization = Column(Boolean, default=False)
    stt_multilingual = Column(Boolean, default=False)

    # Parameters
    system_prompt = Column(Text, default="""<identity>
Eres Andrea, consultora senior de Ubrokers. Tu objetivo es agendar una llamada de 15 min con dueños de empresas para explicar beneficios fiscales 2026.
NO eres una vendedora agresiva; eres una asesora profesional y empática.
</identity>

<style>
- Tono: Profesional, cálido, seguro.
- Idioma: Español Latino (México).
- Pronunciación: Lee "2026" como "dos mil veintiséis".
- Modo: Conversacional, evita scripts rígidos, adapta según cada caso.
</style>

<phases>
   - "¿Le parece bien si le envío la info a su WhatsApp para coordinar?"
   - Obtener Nombre y Teléfono.
</phases>

<rules>
- SI EL USUARIO SE DESVÍA: Responde brevemente y regresa amablemente a la FASE actual.
- SI PIDE PRECIO: "Es un beneficio gratuito para empresas registradas."
- SI NO LE INTERESA: "Entiendo, gracias por su tiempo." (Corta cortésmente).
</rules>""")
    voice_name = Column(String, default="es-MX-DaliaNeural")
    voice_language = Column(String, default="es-MX")
    voice_style = Column(String, nullable=True)
    voice_speed = Column(Float, default=1.0)
    voice_speed_phone = Column(Float, default=0.9)

    # Voice Expression Controls (Azure TTS SSML)
    voice_pitch = Column(Integer, default=0)
    voice_volume = Column(Integer, default=100)
    voice_style_degree = Column(Float, default=1.0)

    # ElevenLabs Specifics
    voice_stability = Column(Float, default=0.5)
    voice_similarity_boost = Column(Float, default=0.75)
    voice_style_exaggeration = Column(Float, default=0.0)
    voice_speaker_boost = Column(Boolean, default=True)
    voice_multilingual = Column(Boolean, default=True)

    # Technical Settings
    tts_latency_optimization = Column(Integer, default=0)
    tts_output_format = Column(String, default="pcm_16000")

    # Humanization
    voice_filler_injection = Column(Boolean, default=False)
    voice_backchanneling = Column(Boolean, default=False)
    text_normalization_rule = Column(String, default="auto")
    pronunciation_dictionary = Column(JSON, nullable=True)

    temperature = Column(Float, default=0.7)

    # Advanced LLM Controls (Browser Profile)
    context_window = Column(Integer, default=10)
    frequency_penalty = Column(Float, default=0.0)
    presence_penalty = Column(Float, default=0.0)
    tool_choice = Column(String, default="auto")
    dynamic_vars_enabled = Column(Boolean, default=False)
    dynamic_vars = Column(JSON, nullable=True)

    background_sound = Column(String, default="none")

    # Flow Control
    idle_timeout = Column(Float, default=10.0)
    idle_message = Column(String, default="¿Hola? ¿Sigue ahí?")
    inactivity_max_retries = Column(Integer, default=3)
    max_duration = Column(Integer, default=600)

    # VAPI / Model & Voice (Browser Defaults)
    first_message = Column(String, default="Hola, soy Andrea de Ubrokers. ¿Me escucha bien?")
    first_message_mode = Column(String, default="speak-first")
    max_tokens = Column(Integer, default=250)

    # Conversation Style Controls
    response_length = Column(String, default="short")
    conversation_tone = Column(String, default="warm")
    conversation_formality = Column(String, default="semi_formal")
    conversation_pacing = Column(String, default="moderate")

    # ---------------- PHONE PROFILE (TWILIO) ----------------
    # Cloned configs for independent tuning
    stt_provider_phone = Column(String, default="azure")
    stt_language_phone = Column(String, default="es-MX")

    # STT Advanced Phone
    stt_model_phone = Column(String, default="nova-2")
    stt_keywords_phone = Column(JSON, nullable=True)
    stt_silence_timeout_phone = Column(Integer, default=500)
    stt_utterance_end_strategy_phone = Column(String, default="default")

    stt_punctuation_phone = Column(Boolean, default=True)
    stt_profanity_filter_phone = Column(Boolean, default=True)
    stt_smart_formatting_phone = Column(Boolean, default=True)

    stt_diarization_phone = Column(Boolean, default=False)
    stt_multilingual_phone = Column(Boolean, default=False)

    llm_provider_phone = Column(String, default="groq")
    llm_model_phone = Column(String, default="llama-3.3-70b-versatile")
    system_prompt_phone = Column(Text, default=None)

    tts_provider_phone = Column(String, default="azure")
    voice_language_phone = Column(String, default="es-MX")
    voice_name_phone = Column(String, default="es-MX-DaliaNeural")
    voice_style_phone = Column(String, nullable=True)

    # Voice Expression Controls - Phone Profile
    voice_pitch_phone = Column(Integer, default=0)
    voice_volume_phone = Column(Integer, default=100)
    voice_style_degree_phone = Column(Float, default=1.0)

    # ElevenLabs Specifics (Phone)
    voice_stability_phone = Column(Float, default=0.5)
    voice_similarity_boost_phone = Column(Float, default=0.75)
    voice_style_exaggeration_phone = Column(Float, default=0.0)
    voice_speaker_boost_phone = Column(Boolean, default=True)
    voice_multilingual_phone = Column(Boolean, default=True)

    # Technical Settings (Phone)
    tts_latency_optimization_phone = Column(Integer, default=0)
    tts_output_format_phone = Column(String, default="pcm_8000")

    # Humanization (Phone)
    voice_filler_injection_phone = Column(Boolean, default=False)
    voice_backchanneling_phone = Column(Boolean, default=False)
    text_normalization_rule_phone = Column(String, default="auto")
    pronunciation_dictionary_phone = Column(JSON, nullable=True)

    temperature_phone = Column(Float, default=0.7)

    # Advanced LLM Controls (Twilio Profile)
    context_window_phone = Column(Integer, default=10)
    frequency_penalty_phone = Column(Float, default=0.0)
    presence_penalty_phone = Column(Float, default=0.0)
    tool_choice_phone = Column(String, default="auto")
    dynamic_vars_enabled_phone = Column(Boolean, default=False)
    dynamic_vars_phone = Column(JSON, nullable=True)

    background_sound_phone = Column(String, default="none")
    first_message_phone = Column(String, default="Hola, soy Andrea de Ubrokers. ¿Me escucha bien?")
    first_message_mode_phone = Column(String, default="speak-first")
    max_tokens_phone = Column(Integer, default=250)

    # Conversation Style Controls (Phone)
    response_length_phone = Column(String, default="short")
    conversation_tone_phone = Column(String, default="warm")
    conversation_formality_phone = Column(String, default="semi_formal")
    conversation_pacing_phone = Column(String, default="moderate")

    initial_silence_timeout_ms_phone = Column(Integer, default=30000)
    input_min_characters_phone = Column(Integer, default=1)
    enable_denoising_phone = Column(Boolean, default=True)


    # TWILIO SPECIFIC (Platform Capabilities)
    twilio_machine_detection = Column(String, default="Enable")
    twilio_record = Column(Boolean, default=False)
    twilio_recording_channels = Column(String, default="dual")
    twilio_trim_silence = Column(Boolean, default=True)


    background_sound_url = Column(String, nullable=True)

    input_min_characters_phone = Column(Integer, default=4)
    hallucination_blacklist = Column(String, default="Pero.,Y...,Mm.,Oye.,Ah.")
    hallucination_blacklist_phone = Column(String, default="Pero.,Y...,Mm.,Oye.,Ah.")
    voice_pacing_ms = Column(Integer, default=300)
    voice_pacing_ms_phone = Column(Integer, default=500)


    # Transcriber & Functions
    silence_timeout_ms = Column(Integer, default=500)
    silence_timeout_ms_phone = Column(Integer, default=2000)

    enable_denoising = Column(Boolean, default=True)
    initial_silence_timeout_ms = Column(Integer, default=30000)

    # VAD Sensitivity
    voice_sensitivity = Column(Integer, default=500)
    voice_sensitivity_phone = Column(Integer, default=3000)

    # Silero VAD Threshold
    vad_threshold = Column(Float, default=0.5)
    vad_threshold_phone = Column(Float, default=0.5)
    vad_threshold_telnyx = Column(Float, default=0.5)

    # ---------------- TELNYX PROFILE ----------------
    # Cloned configs for independent tuning
    stt_provider_telnyx = Column(String, default="azure")
    stt_language_telnyx = Column(String, default="es-MX")

    # STT Advanced Telnyx
    stt_model_telnyx = Column(String, default="nova-2")
    stt_keywords_telnyx = Column(JSON, nullable=True)
    stt_silence_timeout_telnyx = Column(Integer, default=500)
    stt_utterance_end_strategy_telnyx = Column(String, default="default")

    stt_punctuation_telnyx = Column(Boolean, default=True)
    stt_profanity_filter_telnyx = Column(Boolean, default=True)
    stt_smart_formatting_telnyx = Column(Boolean, default=True)

    stt_diarization_telnyx = Column(Boolean, default=False)
    stt_multilingual_telnyx = Column(Boolean, default=False)

    llm_provider_telnyx = Column(String, default="groq")
    llm_model_telnyx = Column(String, default="llama-3.3-70b-versatile")
    system_prompt_telnyx = Column(Text, default=None)

    tts_provider_telnyx = Column(String, default="azure")
    voice_language_telnyx = Column(String, default="es-MX")
    voice_name_telnyx = Column(String, default="es-MX-DaliaNeural")
    voice_style_telnyx = Column(String, nullable=True)

    # Voice Expression Controls - Telnyx Profile
    voice_pitch_telnyx = Column(Integer, default=0)
    voice_volume_telnyx = Column(Integer, default=100)
    voice_style_degree_telnyx = Column(Float, default=1.0)

    # ElevenLabs Specifics (Telnyx)
    voice_stability_telnyx = Column(Float, default=0.5)
    voice_similarity_boost_telnyx = Column(Float, default=0.75)
    voice_style_exaggeration_telnyx = Column(Float, default=0.0)
    voice_speaker_boost_telnyx = Column(Boolean, default=True)
    voice_multilingual_telnyx = Column(Boolean, default=True)

    # Technical Settings (Telnyx)
    tts_latency_optimization_telnyx = Column(Integer, default=0)
    tts_output_format_telnyx = Column(String, default="pcm_8000")

    # Humanization (Telnyx)
    voice_filler_injection_telnyx = Column(Boolean, default=False)
    voice_backchanneling_telnyx = Column(Boolean, default=False)
    text_normalization_rule_telnyx = Column(String, default="auto")
    pronunciation_dictionary_telnyx = Column(JSON, nullable=True)

    temperature_telnyx = Column(Float, default=0.7)

    # Advanced LLM Controls (Telnyx Profile)
    context_window_telnyx = Column(Integer, default=10)
    frequency_penalty_telnyx = Column(Float, default=0.0)
    presence_penalty_telnyx = Column(Float, default=0.0)
    tool_choice_telnyx = Column(String, default="auto")
    dynamic_vars_enabled_telnyx = Column(Boolean, default=False)
    dynamic_vars_telnyx = Column(JSON, nullable=True)

    background_sound_telnyx = Column(String, default="none")
    background_sound_url_telnyx = Column(String, nullable=True)

    first_message_telnyx = Column(String, default="Hola, soy Andrea de Ubrokers. ¿Me escucha bien?")
    first_message_mode_telnyx = Column(String, default="speak-first")
    max_tokens_telnyx = Column(Integer, default=250)

    # Conversation Style Controls (Telnyx)
    response_length_telnyx = Column(String, default="short")
    conversation_tone_telnyx = Column(String, default="warm")
    conversation_formality_telnyx = Column(String, default="semi_formal")
    conversation_pacing_telnyx = Column(String, default="moderate")

    # Tools Configuration (Telnyx)
    client_tools_enabled_telnyx = Column(Boolean, default=False)

    initial_silence_timeout_ms_telnyx = Column(Integer, default=30000)
    input_min_characters_telnyx = Column(Integer, default=4)
    enable_denoising_telnyx = Column(Boolean, default=True)

    voice_pacing_ms_telnyx = Column(Integer, default=500)
    silence_timeout_ms_telnyx = Column(Integer, default=2000)
    interruption_threshold_telnyx = Column(Integer, default=2)
    hallucination_blacklist_telnyx = Column(String, default="Pero.,Y...,Mm.,Oye.,Ah.")
    voice_speed_telnyx = Column(Float, default=0.9)

    # Telnyx Native Features
    voice_sensitivity_telnyx = Column(Integer, default=3000)
    enable_krisp_telnyx = Column(Boolean, default=True)
    noise_suppression_level_telnyx = Column(String, default="balanced")
    enable_vad_telnyx = Column(Boolean, default=True)
    audio_codec_telnyx = Column(String, default="PCMU")
    enable_backchannel_telnyx = Column(Boolean, default=False)

    # Telnyx Advanced (Flow & Features)
    idle_timeout_telnyx = Column(Float, default=20.0)
    max_duration_telnyx = Column(Integer, default=600)
    idle_message_telnyx = Column(String, default="¿Hola? ¿Sigue ahí?")
    enable_recording_telnyx = Column(Boolean, default=False)
    amd_config_telnyx = Column(String, default="disabled")

    # Telnyx System & Safety (Isolation)
    max_retries_telnyx = Column(Integer, default=3)
    concurrency_limit_telnyx = Column(Integer, nullable=True)
    daily_spend_limit_telnyx = Column(Float, nullable=True)
    environment_tag_telnyx = Column(String, default="development")
    privacy_mode_telnyx = Column(Boolean, default=False)
    audit_log_enabled_telnyx = Column(Boolean, default=False)

    enable_end_call = Column(Boolean, default=True)
    enable_dial_keypad = Column(Boolean, default=False)
    transfer_phone_number = Column(String, nullable=True)

    # ---------------- CRM INTEGRATION ----------------
    crm_enabled = Column(Boolean, default=False)
    baserow_token = Column(String, nullable=True)
    baserow_table_id = Column(Integer, nullable=True)

    # ---------------- WEBHOOK INTEGRATION ----------------
    webhook_url = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)

    # =============================================================================
    # FLOW & ORCHESTRATION
    # =============================================================================

    # --- 1. BARGE-IN & INTERRUPTIONS ---
    # Base
    barge_in_enabled = Column(Boolean, default=True)
    interruption_sensitivity = Column(Float, default=0.5)
    interruption_phrases = Column(JSON, nullable=True)
    # Phone
    barge_in_enabled_phone = Column(Boolean, default=True)
    interruption_sensitivity_phone = Column(Float, default=0.8)
    interruption_phrases_phone = Column(JSON, nullable=True)
    # Telnyx
    barge_in_enabled_telnyx = Column(Boolean, default=True)
    interruption_sensitivity_telnyx = Column(Float, default=0.8)
    interruption_phrases_telnyx = Column(JSON, nullable=True)

    # --- 2. VOICEMAIL & MACHINE ---
    # Base
    voicemail_detection_enabled = Column(Boolean, default=False)
    voicemail_message = Column(Text, default="Hola, llamaba de Ubrokers. Le enviaré un WhatsApp.")
    machine_detection_sensitivity = Column(Float, default=0.7)
    # Phone
    voicemail_detection_enabled_phone = Column(Boolean, default=True)
    voicemail_message_phone = Column(Text, default="Hola, llamaba de Ubrokers. Le enviaré un WhatsApp.")
    machine_detection_sensitivity_phone = Column(Float, default=0.7)
    # Telnyx
    voicemail_detection_enabled_telnyx = Column(Boolean, default=True)
    voicemail_message_telnyx = Column(Text, default="Hola, llamaba de Ubrokers. Le enviaré un WhatsApp.")
    machine_detection_sensitivity_telnyx = Column(Float, default=0.7)

    # --- 3. PACING & NATURALNESS ---
    # Base
    response_delay_seconds = Column(Float, default=0.5)
    wait_for_greeting = Column(Boolean, default=True)
    hyphenation_enabled = Column(Boolean, default=False)
    end_call_phrases = Column(JSON, nullable=True)
    # Phone
    response_delay_seconds_phone = Column(Float, default=0.8)
    wait_for_greeting_phone = Column(Boolean, default=True)
    hyphenation_enabled_phone = Column(Boolean, default=False)
    end_call_phrases_phone = Column(JSON, nullable=True)
    # Telnyx
    response_delay_seconds_telnyx = Column(Float, default=0.8)
    wait_for_greeting_telnyx = Column(Boolean, default=True)
    hyphenation_enabled_telnyx = Column(Boolean, default=False)
    end_call_phrases_telnyx = Column(JSON, nullable=True)

    # =============================================================================
    # TELEPHONY TOOLS
    # =============================================================================

    # --- 1. CREDENTIALS (BYOC) ---
    # Phone (Twilio)
    twilio_account_sid = Column(String, nullable=True)
    twilio_auth_token = Column(String, nullable=True)
    twilio_from_number = Column(String, nullable=True)
    # Telnyx
    telnyx_api_key = Column(String, nullable=True)

    telnyx_connection_id = Column(String, nullable=True)

    # --- 2. INFRASTRUCTURE & SIP ---
    # Phone
    caller_id_phone = Column(String, nullable=True)
    sip_trunk_uri_phone = Column(String, nullable=True)
    sip_auth_user_phone = Column(String, nullable=True)
    sip_auth_pass_phone = Column(String, nullable=True)
    fallback_number_phone = Column(String, nullable=True)
    geo_region_phone = Column(String, default="us-east-1")
    # Telnyx
    caller_id_telnyx = Column(String, nullable=True)
    sip_trunk_uri_telnyx = Column(String, nullable=True)
    sip_auth_user_telnyx = Column(String, nullable=True)
    sip_auth_pass_telnyx = Column(String, nullable=True)
    fallback_number_telnyx = Column(String, nullable=True)
    geo_region_telnyx = Column(String, default="us-central")

    # =============================================================================
    # TOOLS & ACTIONS (PHASE VI)
    # =============================================================================

    # --- 1. FUNCTION CALLING ---
    # Base
    tools_schema = Column(JSON, nullable=True)  # OpenAI Tools Schema
    tools_async = Column(Boolean, default=False)
    client_tools_enabled = Column(Boolean, default=False)
    # Phone
    # Phone / Telnyx Tools columns removed (DUPLICATES - See FUNCTION CALLING section below)

    # --- 2. SERVER CONFIG (n8n/Webhook) ---
    # Base
    tool_server_url = Column(String, nullable=True)
    tool_server_secret = Column(String, nullable=True)
    tool_timeout_ms = Column(Integer, default=5000)
    tool_retry_count = Column(Integer, default=0)
    tool_error_msg = Column(String, default="Lo siento, hubo un error al procesar tu solicitud.")
    # Phone
    tool_server_url_phone = Column(String, nullable=True)
    tool_server_secret_phone = Column(String, nullable=True)
    tool_timeout_ms_phone = Column(Integer, default=5000)
    tool_retry_count_phone = Column(Integer, default=0)
    tool_error_msg_phone = Column(String, default="Lo siento, hubo un error técnico.")
    # Telnyx
    tool_server_url_telnyx = Column(String, nullable=True)
    tool_server_secret_telnyx = Column(String, nullable=True)
    tool_timeout_ms_telnyx = Column(Integer, default=5000)
    tool_retry_count_telnyx = Column(Integer, default=0)
    tool_error_msg_telnyx = Column(String, default="Lo siento, hubo un error técnico.")

    # --- 3. SERVER CONFIG (Telnyx Integrations) ---
    webhook_url_telnyx = Column(String, nullable=True)
    webhook_secret_telnyx = Column(String, nullable=True)
    crm_enabled_telnyx = Column(Boolean, default=False)
    baserow_token_telnyx = Column(String, nullable=True)
    baserow_table_id_telnyx = Column(Integer, nullable=True)

    # --- 3. SECURITY & INJECTION ---
    # Base
    redact_params = Column(JSON, nullable=True)  # ["password", "ssn"]
    transfer_whitelist = Column(JSON, nullable=True)  # ["+1555...", "+52..."]
    state_injection_enabled = Column(Boolean, default=True)
    # Phone
    redact_params_phone = Column(JSON, nullable=True)
    transfer_whitelist_phone = Column(JSON, nullable=True)
    state_injection_enabled_phone = Column(Boolean, default=True)
    # Telnyx
    redact_params_telnyx = Column(JSON, nullable=True)
    transfer_whitelist_telnyx = Column(JSON, nullable=True)
    state_injection_enabled_telnyx = Column(Boolean, default=True)

    # --- 3. RECORDING & COMPLIANCE ---
    # Phone
    recording_enabled_phone = Column(Boolean, default=False)
    recording_channels_phone = Column(String, default="mono")
    hipaa_enabled_phone = Column(Boolean, default=False)
    # Telnyx
    recording_channels_telnyx = Column(String, default="dual")
    hipaa_enabled_telnyx = Column(Boolean, default=False)

    # --- 4. CALL FEATURES ---
    # Phone
    transfer_type_phone = Column(String, default="cold")
    dtmf_generation_enabled_phone = Column(Boolean, default=False)
    dtmf_listening_enabled_phone = Column(Boolean, default=False)
    # Telnyx
    transfer_type_telnyx = Column(String, default="cold")
    dtmf_generation_enabled_telnyx = Column(Boolean, default=False)
    dtmf_listening_enabled_telnyx = Column(Boolean, default=False)

    # =============================================================================
    # FUNCTION CALLING (Tools & Actions)
    # =============================================================================

    # --- 1. SERVER CONFIG ---
    # Base (Browser)
    tool_server_url = Column(String, nullable=True)
    tool_server_secret = Column(String, nullable=True)
    tool_timeout_ms = Column(Integer, default=5000)
    tool_error_msg = Column(Text, default="Lo siento, hubo un error técnico.")
    # Phone
    tool_server_url_phone = Column(String, nullable=True)
    tool_server_secret_phone = Column(String, nullable=True)
    tool_timeout_ms_phone = Column(Integer, default=5000)
    tool_error_msg_phone = Column(Text, default="Lo siento, hubo un error técnico.")
    # Telnyx
    tool_server_url_telnyx = Column(String, nullable=True)
    tool_server_secret_telnyx = Column(String, nullable=True)
    tool_timeout_ms_telnyx = Column(Integer, default=5000)
    tool_error_msg_telnyx = Column(Text, default="Lo siento, hubo un error técnico.")

    # --- 2. TOOL DEFINITIONS ---
    # Base
    tools_schema = Column(JSON, nullable=True)
    async_tools = Column(Boolean, default=False)
    client_tools_enabled = Column(Boolean, default=False)
    # Phone
    tools_schema_phone = Column(JSON, nullable=True)
    async_tools_phone = Column(Boolean, default=False)
    # Telnyx
    tools_schema_telnyx = Column(JSON, nullable=True)
    async_tools_telnyx = Column(Boolean, default=False)

    # --- 3. SECURITY ---
    # Base
    redact_params = Column(JSON, nullable=True)
    state_injection_enabled = Column(Boolean, default=False)
    transfer_whitelist = Column(JSON, nullable=True)
    # Phone
    redact_params_phone = Column(JSON, nullable=True)
    state_injection_enabled_phone = Column(Boolean, default=False)
    transfer_whitelist_phone = Column(JSON, nullable=True)
    # Telnyx
    redact_params_telnyx = Column(JSON, nullable=True)
    state_injection_enabled_telnyx = Column(Boolean, default=False)
    transfer_whitelist_telnyx = Column(JSON, nullable=True)

    # =============================================================================
    # RATE LIMITING & PROVIDER LIMITS
    # =============================================================================
    # Rate Limiting por Endpoint (requests/minuto)
    rate_limit_global = Column(Integer, nullable=True, default=200)
    rate_limit_twilio = Column(Integer, nullable=True, default=30)
    rate_limit_telnyx = Column(Integer, nullable=True, default=50)
    rate_limit_websocket = Column(Integer, nullable=True, default=100)

    # Provider Limits
    limit_groq_tokens_per_min = Column(Integer, nullable=True, default=100000)
    limit_azure_requests_per_min = Column(Integer, nullable=True, default=100)
    limit_twilio_calls_per_hour = Column(Integer, nullable=True, default=100)
    limit_telnyx_calls_per_hour = Column(Integer, nullable=True, default=100)

    # =============================================================================
    # SYSTEM & GOVERNANCE (PHASE VIII)
    # =============================================================================
    concurrency_limit = Column(Integer, default=10)
    spend_limit_daily = Column(Float, default=50.0)
    environment = Column(String, default="development")
    privacy_mode = Column(Boolean, default=False)
    audit_log_enabled = Column(Boolean, default=True)

    # =============================================================================
    # ADVANCED: QUALITY & LIMITS (PHASE IX)
    # =============================================================================
    noise_suppression_level = Column(String, default="balanced")
    audio_codec = Column(String, default="PCMU")
    enable_backchannel = Column(Boolean, default=False)

    max_duration = Column(Integer, default=600)
    inactivity_max_retries = Column(Integer, default=2)
    idle_message = Column(Text, default="¿Sigues ahí?")

    # =============================================================================
    # ANALYSIS & DATA (Post-Call)
    # =============================================================================

    # --- 1. ANALYSIS & EXTRACTION ---
    # Base
    analysis_prompt = Column(Text, nullable=True)
    success_rubric = Column(Text, nullable=True)
    extraction_schema = Column(JSON, nullable=True)
    # Phone
    analysis_prompt_phone = Column(Text, nullable=True)
    success_rubric_phone = Column(Text, nullable=True)
    extraction_schema_phone = Column(JSON, nullable=True)
    # Telnyx
    analysis_prompt_telnyx = Column(Text, nullable=True)
    success_rubric_telnyx = Column(Text, nullable=True)
    extraction_schema_telnyx = Column(JSON, nullable=True)

    # --- 2. METRICS & FORMAT ---
    # Base
    sentiment_analysis = Column(Boolean, default=False)
    transcript_format = Column(String, default="text")
    cost_tracking_enabled = Column(Boolean, default=True)
    # Phone
    sentiment_analysis_phone = Column(Boolean, default=False)
    transcript_format_phone = Column(String, default="text")
    cost_tracking_enabled_phone = Column(Boolean, default=True)
    # Telnyx
    sentiment_analysis_telnyx = Column(Boolean, default=False)
    transcript_format_telnyx = Column(String, default="text")
    cost_tracking_enabled_telnyx = Column(Boolean, default=True)

    # --- 3. OUTPUT & COMPLIANCE ---
    # Base
    log_webhook_url = Column(String, nullable=True)
    pii_redaction_enabled = Column(Boolean, default=False)
    retention_days = Column(Integer, default=30)
    # Phone
    webhook_url_phone = Column(String, nullable=True)
    webhook_secret_phone = Column(String, nullable=True)
    log_webhook_url_phone = Column(String, nullable=True)
    pii_redaction_enabled_phone = Column(Boolean, default=False)
    retention_days_phone = Column(Integer, default=30)
    # Telnyx
    webhook_url_telnyx = Column(String, nullable=True)
    webhook_secret_telnyx = Column(String, nullable=True)
    log_webhook_url_telnyx = Column(String, nullable=True)
    pii_redaction_enabled_telnyx = Column(Boolean, default=False)
    retention_days_telnyx = Column(Integer, default=30)

    # =============================================================================
    # SYSTEM & DEVOPS
    # =============================================================================

    # --- 1. GOVERNANCE & LIMITS ---
    concurrency_limit = Column(Integer, default=10)
    spend_limit_daily = Column(Float, default=50.0)
    environment = Column(String, default="development")

    # --- 2. SECURITY & IDENTITY ---
    custom_headers = Column(JSON, nullable=True)
    sub_account_id = Column(String, nullable=True)
    allowed_api_keys = Column(JSON, nullable=True)
    audit_log_enabled = Column(Boolean, default=True)
    privacy_mode = Column(Boolean, default=False)

    # Phone/Telnyx Overrides
    environment_phone = Column(String, nullable=True)
    privacy_mode_phone = Column(Boolean, default=False)
    environment_telnyx = Column(String, nullable=True)
    privacy_mode_telnyx = Column(Boolean, default=False)

    # =============================================================================
    # PROFILE CONFIGURATION HELPERS
    # =============================================================================

    def _get_suffix(self, profile_type: str) -> str:
        """
        Get column suffix for profile type.

        Centralizes the suffix mapping logic that was previously duplicated
        across stt.py, tts.py, vad.py, config_utils.py, etc.

        Args:
            profile_type: Profile identifier ("browser", "twilio", "telnyx", "simulator")

        Returns:
            Column suffix string ("", "_phone", "_telnyx")

        Examples:
            >>> config._get_suffix("browser")
            ""
            >>> config._get_suffix("twilio")
            "_phone"
            >>> config._get_suffix("telnyx")
            "_telnyx"
        """
        suffix_map = {
            "browser": "",
            "simulator": "",  # Simulator uses browser config
            "twilio": "_phone",
            "telnyx": "_telnyx"
        }
        normalized = profile_type.lower().strip() if profile_type else "browser"
        return suffix_map.get(normalized, "")

    def get_profile(self, profile_type: str) -> 'ProfileConfigSchema':
        """
        Get type-safe profile configuration.

        Returns a Pydantic schema with all profile-specific config values.
        Eliminates need for manual suffix concatenation in application code.

        Args:
            profile_type: Profile identifier ("browser", "twilio", "telnyx")

        Returns:
            ProfileConfigSchema with values from database columns

        Raises:
            ImportError: If ProfileConfigSchema not available

        Examples:
            >>> config = await db.get_agent_config()
            >>> browser_profile = config.get_profile("browser")
            >>> print(browser_profile.voice_speed)  # 1.0

            >>> twilio_profile = config.get_profile("twilio")
            >>> print(twilio_profile.voice_speed)  # 0.9

        Benefits:
            - Type safety: IDE autocomplete, mypy validation
            - No manual suffix logic in caller code
            - Centralized: changes to schema don't affect callers
        """
        from app.schemas.profile_config import ProfileConfigSchema

        suffix = self._get_suffix(profile_type)
        data = {}

        # Iterate over all fields in Pydantic schema
        for field_name in ProfileConfigSchema.model_fields:
            db_column = f"{field_name}{suffix}"

            # Get value from DB column if it exists
            if hasattr(self, db_column):
                value = getattr(self, db_column)
                # Only include non-None values (let Pydantic use defaults for None)
                if value is not None:
                    data[field_name] = value

        # Pydantic will fill in defaults for any missing fields
        return ProfileConfigSchema(**data)

    def update_profile(self, profile_type: str, updates: 'ProfileConfigSchema') -> None:
        """
        Update profile configuration from Pydantic schema.

        Safely updates database columns with values from ProfileConfigSchema.
        Only updates fields that were explicitly set (exclude_unset=True).

        Args:
            profile_type: Profile identifier ("browser", "twilio", "telnyx")
            updates: ProfileConfigSchema with new values

        Examples:
            >>> from app.schemas.profile_config import ProfileConfigSchema
            >>>
            >>> # Partial update (only voice_speed)
            >>> updates = ProfileConfigSchema(voice_speed=1.5)
            >>> config.update_profile("twilio", updates)
            >>> # Only voice_speed_phone is updated, other fields untouched

            >>> # Full update
            >>> updates = ProfileConfigSchema(
            ...     voice_speed=1.2,
            ...     temperature=0.8,
            ...     context_window=15
            ... )
            >>> config.update_profile("browser", updates)

        Notes:
            - This method modifies the model in-memory.
            - Caller must commit session to persist changes to database.
            - Profiles are isolated: updating "twilio" doesn't affect "browser"
        """
        suffix = self._get_suffix(profile_type)

        # Only update fields that were explicitly set by caller
        # exclude_unset=True prevents overwriting with Pydantic defaults
        for field_name, value in updates.model_dump(exclude_unset=True).items():
            db_column = f"{field_name}{suffix}"

            # Only update if column exists in model
            if hasattr(self, db_column):
                setattr(self, db_column, value)

