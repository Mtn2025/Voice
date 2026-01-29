from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass

class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    client_type = Column(String, default="simulator") # simulator, twilio, telnyx
    extracted_data = Column(JSON, nullable=True) # New

    transcripts = relationship("Transcript", back_populates="call")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), index=True)
    role = Column(String) # user or assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="transcripts")

class AgentConfig(Base):
    """
    Agent Configuration (Denormalized by Design).

    This table contains 100+ columns with duplicated fields across three profiles:
    - Base profile: Browser/Simulator calls
    - Phone profile (_phone suffix): Twilio calls
    - Telnyx profile (_telnyx suffix): Telnyx calls

    ARCHITECTURAL DECISION:
    Intentionally denormalized for operational simplicity in single-tenant deployments.

    Rationale:
    - Single-tenant app (one config per deployment)
    - Simple queries (no JOINs needed)
    - Easy Coolify deployment
    - Low volume (1-10 records max)
    - Debugging simplicity

    Trade-offs:
    - Schema duplication across profiles
    - Wide table (100+ columns)
    - Violates 3NF normalization

    When to normalize:
    - Multi-tenant support required
    - 100+ distinct configurations
    - Complex auditing needs
    - Horizontal scaling required

    Last reviewed: 2026-01-06
    """
    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, default="default")

    # Providers
    stt_provider = Column(String, default="azure")
    stt_language = Column(String, default="es-MX") # Add stt_language
    llm_provider = Column(String, default="groq")
    llm_model = Column(String, default="llama-3.3-70b-versatile")
    extraction_model = Column(String, default="llama-3.1-8b-instant")
    interruption_threshold = Column(Integer, default=5) # Noise Tolerance (Browser)
    interruption_threshold_phone = Column(Integer, default=2) # Noise Tolerance (Phone) - Lower default for sharper interruptions
    tts_provider = Column(String, default="azure")

    # STT Advanced (Controls 32-40)
    stt_model = Column(String, default="nova-2") # 32. Model
    stt_keywords = Column(JSON, nullable=True) # 33. Keywords
    stt_silence_timeout = Column(Integer, default=500) # 34. Endpointing
    stt_utterance_end_strategy = Column(String, default="default") # 35. Utterance End

    # STT Formatting & Filters
    stt_punctuation = Column(Boolean, default=True) # 36. Punctuation
    stt_profanity_filter = Column(Boolean, default=True) # 37. Profanity
    stt_smart_formatting = Column(Boolean, default=True) # 38. Smart Formatting

    # STT Advanced Features
    stt_diarization = Column(Boolean, default=False) # 39. Diarization
    stt_multilingual = Column(Boolean, default=False) # 40. Multi-Language

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

   - "¿Le parece bien si le envío la info a su WhatsApp para coordinar?"
   - Obtener Nombre y Teléfono.
</phases>

<rules>
- SI EL USUARIO SE DESVÍA: Responde brevemente y regresa amablemente a la FASE actual.
- SI PIDE PRECIO: "Es un beneficio gratuito para empresas registradas."
- SI NO LE INTERESA: "Entiendo, gracias por su tiempo." (Corta cortésmente).
</rules>""")
    voice_name = Column(String, default="es-MX-DaliaNeural")
    voice_language = Column(String, default="es-MX")  # FIX: Added missing field for Browser profile
    voice_style = Column(String, nullable=True) # New: Style/Emotion
    voice_speed = Column(Float, default=1.0)
    voice_speed_phone = Column(Float, default=0.9) # Slower for phone
    
    # Voice Expression Controls (Azure TTS SSML)
    voice_pitch = Column(Integer, default=0)  # Pitch in semitones (-12 to +12)
    voice_volume = Column(Integer, default=100)  # Volume 0-100
    voice_style_degree = Column(Float, default=1.0)  # Style intensity 0.5-2.0
    
    # NEW: ElevenLabs Specifics (Conditional)
    voice_stability = Column(Float, default=0.5)
    voice_similarity_boost = Column(Float, default=0.75)
    voice_style_exaggeration = Column(Float, default=0.0)
    voice_speaker_boost = Column(Boolean, default=True)
    voice_multilingual = Column(Boolean, default=True)
    
    # NEW: Technical Settings
    tts_latency_optimization = Column(Integer, default=0) # 0-4
    tts_output_format = Column(String, default="pcm_16000")
    
    # NEW: Humanization
    voice_filler_injection = Column(Boolean, default=False)
    voice_backchanneling = Column(Boolean, default=False)
    text_normalization_rule = Column(String, default="auto")
    pronunciation_dictionary = Column(JSON, nullable=True)

    temperature = Column(Float, default=0.7)
    
    # NEW: Advanced LLM Controls (Browser Profile)
    context_window = Column(Integer, default=10)  # Number of previous messages to remember
    frequency_penalty = Column(Float, default=0.0)  # Penalize repeated words (0.0-2.0)
    presence_penalty = Column(Float, default=0.0)   # Encourage new topics (0.0-2.0)
    tool_choice = Column(String, default="auto")    # auto, required, none
    dynamic_vars_enabled = Column(Boolean, default=False)  # Enable {variable} injection
    dynamic_vars = Column(JSON, nullable=True)      # {"nombre": "Juan", "empresa": "Acme"}
    
    background_sound = Column(String, default="none") # none, office, cafe, call_center

    # Flow Control
    idle_timeout = Column(Float, default=10.0) # Seconds to wait before prompt
    idle_message = Column(String, default="¿Hola? ¿Sigue ahí?")
    inactivity_max_retries = Column(Integer, default=3) # New: Retries before hangup
    max_duration = Column(Integer, default=600) # Max call seconds

    # VAPI Stage 1: Model & Voice
    # VAPI Stage 1: Model & Voice (Browser Defaults)
    first_message = Column(String, default="Hola, soy Andrea de Ubrokers. ¿Me escucha bien?")
    first_message_mode = Column(String, default="speak-first") # speak-first, wait-for-user, speak-first-dynamic
    max_tokens = Column(Integer, default=250)
    
    # NEW: Conversation Style Controls (User-configurable behavior)
    response_length = Column(String, default="short")  
    # Options: very_short, short, medium, long, detailed
    
    conversation_tone = Column(String, default="warm")  
    # Options: professional, friendly, warm, enthusiastic, neutral, empathetic
    
    conversation_formality = Column(String, default="semi_formal")  
    # Options: very_formal, formal, semi_formal, casual, very_casual
    
    conversation_pacing = Column(String, default="moderate")  
    # Options: fast, moderate, relaxed

    # ---------------- PHONE PROFILE (TWILIO) ----------------
    # Cloned configs for independent tuning
    stt_provider_phone = Column(String, default="azure")
    stt_language_phone = Column(String, default="es-MX")
    
    # STT Advanced Phone (Controls 32-40 Override)
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
    system_prompt_phone = Column(Text, default=None) # If None, fallback to system_prompt

    tts_provider_phone = Column(String, default="azure")  # FIX: Added missing field
    voice_language_phone = Column(String, default="es-MX")  # FIX: Added missing field
    voice_name_phone = Column(String, default="es-MX-DaliaNeural")
    voice_style_phone = Column(String, nullable=True)
    
    # Voice Expression Controls - Phone Profile
    voice_pitch_phone = Column(Integer, default=0)
    voice_volume_phone = Column(Integer, default=100)
    voice_style_degree_phone = Column(Float, default=1.0)
    
    # NEW: ElevenLabs Specifics (Phone)
    voice_stability_phone = Column(Float, default=0.5)
    voice_similarity_boost_phone = Column(Float, default=0.75)
    voice_style_exaggeration_phone = Column(Float, default=0.0)
    voice_speaker_boost_phone = Column(Boolean, default=True)
    voice_multilingual_phone = Column(Boolean, default=True)
    
    # NEW: Technical Settings (Phone)
    tts_latency_optimization_phone = Column(Integer, default=0)
    tts_output_format_phone = Column(String, default="pcm_8000") # Phone default
    
    # NEW: Humanization (Phone)
    voice_filler_injection_phone = Column(Boolean, default=False)
    voice_backchanneling_phone = Column(Boolean, default=False)
    text_normalization_rule_phone = Column(String, default="auto")
    pronunciation_dictionary_phone = Column(JSON, nullable=True)

    temperature_phone = Column(Float, default=0.7)
    
    # NEW: Advanced LLM Controls (Twilio Profile)
    context_window_phone = Column(Integer, default=10)
    frequency_penalty_phone = Column(Float, default=0.0)
    presence_penalty_phone = Column(Float, default=0.0)
    tool_choice_phone = Column(String, default="auto")
    dynamic_vars_enabled_phone = Column(Boolean, default=False)
    dynamic_vars_phone = Column(JSON, nullable=True)
    
    background_sound_phone = Column(String, default="none")  # FIX: Added missing field

    first_message_phone = Column(String, default="Hola, soy Andrea de Ubrokers. ¿Me escucha bien?")
    first_message_mode_phone = Column(String, default="speak-first")
    max_tokens_phone = Column(Integer, default=250)

    initial_silence_timeout_ms_phone = Column(Integer, default=30000)
    input_min_characters_phone = Column(Integer, default=1)
    enable_denoising_phone = Column(Boolean, default=True)
    extra_settings_phone = Column(JSON, nullable=True)


    # TWILIO SPECIFIC (Platform Capabilities)
    twilio_machine_detection = Column(String, default="Enable") # Enable, Disable, DetectMessageEnd
    twilio_record = Column(Boolean, default=False)
    twilio_recording_channels = Column(String, default="dual")
    twilio_trim_silence = Column(Boolean, default=True)
    # ---------------------------------------------------------

    voice_id_manual = Column(String, nullable=True) # Override standard list
    background_sound_url = Column(String, nullable=True) # External URL for ambient noise
    input_min_characters = Column(Integer, default=2) # Minimum chars to be valid (Updated default)
    input_min_characters_phone = Column(Integer, default=4) # Phone usually needs lower
    hallucination_blacklist = Column(String, default="Pero.,Y...,Mm.,Oye.,Ah.") # Browser Blacklist
    hallucination_blacklist_phone = Column(String, default="Pero.,Y...,Mm.,Oye.,Ah.") # Phone Blacklist
    voice_pacing_ms = Column(Integer, default=300) # Response Delay (Browser)
    voice_pacing_ms_phone = Column(Integer, default=500) # Response Delay (Phone)
    punctuation_boundaries = Column(String, nullable=True)

    # VAPI Stage 2: Transcriber & Functions
    silence_timeout_ms = Column(Integer, default=500) # Speech end silence
    silence_timeout_ms_phone = Column(Integer, default=2000) # Phone silence timeout (Higher for latency)
    segmentation_max_time = Column(Integer, default=30000) # ms (max phrase duration)
    segmentation_strategy = Column(String, default="default") # default, time, semantic
    enable_denoising = Column(Boolean, default=True)
    initial_silence_timeout_ms = Column(Integer, default=30000) # Time to wait for start of speech

    # VAD Sensitivity (Lower = More Sensitive)
    voice_sensitivity = Column(Integer, default=500)
    voice_sensitivity_phone = Column(Integer, default=3000) # Phone: Higher threshold to filter noise
    
    # Silero VAD Threshold (0.0 - 1.0)
    vad_threshold = Column(Float, default=0.5)
    vad_threshold_phone = Column(Float, default=0.5)
    vad_threshold_telnyx = Column(Float, default=0.5)

    # ---------------- TELNYX PROFILE ----------------
    # Cloned configs for independent tuning
    stt_provider_telnyx = Column(String, default="azure")
    stt_language_telnyx = Column(String, default="es-MX")
    
    # STT Advanced Telnyx (Controls 32-40 Override)
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

    tts_provider_telnyx = Column(String, default="azure")  # FIX: Added missing field
    voice_language_telnyx = Column(String, default="es-MX")  # FIX: Added missing field
    voice_name_telnyx = Column(String, default="es-MX-DaliaNeural")
    voice_style_telnyx = Column(String, nullable=True)
    
    # Voice Expression Controls - Telnyx Profile
    voice_pitch_telnyx = Column(Integer, default=0)
    voice_volume_telnyx = Column(Integer, default=100)
    voice_style_degree_telnyx = Column(Float, default=1.0)
    
    # NEW: ElevenLabs Specifics (Telnyx)
    voice_stability_telnyx = Column(Float, default=0.5)
    voice_similarity_boost_telnyx = Column(Float, default=0.75)
    voice_style_exaggeration_telnyx = Column(Float, default=0.0)
    voice_speaker_boost_telnyx = Column(Boolean, default=True)
    voice_multilingual_telnyx = Column(Boolean, default=True)
    
    # NEW: Technical Settings (Telnyx)
    tts_latency_optimization_telnyx = Column(Integer, default=0)
    tts_output_format_telnyx = Column(String, default="pcm_8000") # Phone default
    
    # NEW: Humanization (Telnyx)
    voice_filler_injection_telnyx = Column(Boolean, default=False)
    voice_backchanneling_telnyx = Column(Boolean, default=False)
    text_normalization_rule_telnyx = Column(String, default="auto")
    pronunciation_dictionary_telnyx = Column(JSON, nullable=True)

    temperature_telnyx = Column(Float, default=0.7)
    
    # NEW: Advanced LLM Controls (Telnyx Profile)
    context_window_telnyx = Column(Integer, default=10)
    frequency_penalty_telnyx = Column(Float, default=0.0)
    presence_penalty_telnyx = Column(Float, default=0.0)
    tool_choice_telnyx = Column(String, default="auto")
    dynamic_vars_enabled_telnyx = Column(Boolean, default=False)
    dynamic_vars_telnyx = Column(JSON, nullable=True)
    
    background_sound_telnyx = Column(String, default="none")  # FIX: Added missing field
    background_sound_url_telnyx = Column(String, nullable=True)  # FIX: Added missing field

    first_message_telnyx = Column(String, default="Hola, soy Andrea de Ubrokers. ¿Me escucha bien?")
    first_message_mode_telnyx = Column(String, default="speak-first")
    max_tokens_telnyx = Column(Integer, default=250)

    initial_silence_timeout_ms_telnyx = Column(Integer, default=30000)
    input_min_characters_telnyx = Column(Integer, default=4)
    enable_denoising_telnyx = Column(Boolean, default=True)

    voice_pacing_ms_telnyx = Column(Integer, default=500)
    silence_timeout_ms_telnyx = Column(Integer, default=2000)
    interruption_threshold_telnyx = Column(Integer, default=2)
    hallucination_blacklist_telnyx = Column(String, default="Pero.,Y...,Mm.,Oye.,Ah.")
    voice_speed_telnyx = Column(Float, default=0.9)

    # Telnyx Native Features
    voice_sensitivity_telnyx = Column(Integer, default=3000)  # Voice activation threshold (RMS)
    enable_krisp_telnyx = Column(Boolean, default=True)       # Krisp noise suppression (native)
    noise_suppression_level = Column(String, default="balanced") # off, low, balanced, high
    enable_vad_telnyx = Column(Boolean, default=True)         # Voice Activity Detection (native)
    audio_codec = Column(String, default="PCMU") # PCMU, PCMA, OPUS
    enable_backchannel = Column(Boolean, default=False) # Active Listening (Yeah, uh-huh)

    # Telnyx Advanced (Flow & Features)
    idle_timeout_telnyx = Column(Float, default=20.0)         # Independent idle timeout
    max_duration_telnyx = Column(Integer, default=600)        # Independent max duration
    idle_message_telnyx = Column(String, default="¿Hola? ¿Sigue ahí?")
    enable_recording_telnyx = Column(Boolean, default=False)  # Native Recording
    amd_config_telnyx = Column(String, default="disabled")    # disabled, detect, detect_hangup
    # ------------------------------------------------

    enable_end_call = Column(Boolean, default=True)
    enable_dial_keypad = Column(Boolean, default=False)
    transfer_phone_number = Column(String, nullable=True)

    # ---------------- CRM INTEGRATION (BASEROW) ----------------
    crm_enabled = Column(Boolean, default=False)
    baserow_token = Column(String, nullable=True)
    baserow_table_id = Column(Integer, nullable=True)
    
    # ---------------- WEBHOOK INTEGRATION (Phase 9) ----------------
    webhook_url = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True)
    # ---------------------------------------------------------------

    # Flow Control (Legacy/Simple)


    is_active = Column(Boolean, default=True)

    # =============================================================================
    # PHASE IV: FLOW & ORCHESTRATION (The "Magic" of Real-time)
    # =============================================================================
    
    # --- 1. BARGE-IN & INTERRUPTIONS (41-43) ---
    # Base
    barge_in_enabled = Column(Boolean, default=True) # 42
    interruption_sensitivity = Column(Float, default=0.5) # 41 (0.0=Hard to Interrupt, 1.0=Easy)
    interruption_phrases = Column(JSON, nullable=True) # 43 (Phrases that FORCE interruption)
    # Phone
    barge_in_enabled_phone = Column(Boolean, default=True)
    interruption_sensitivity_phone = Column(Float, default=0.8) # Phone usually needs higher sensitivity
    interruption_phrases_phone = Column(JSON, nullable=True)
    # Telnyx
    barge_in_enabled_telnyx = Column(Boolean, default=True)
    interruption_sensitivity_telnyx = Column(Float, default=0.8)
    interruption_phrases_telnyx = Column(JSON, nullable=True)

    # --- 2. VOICEMAIL & MACHINE (46-48) ---
    # Base
    voicemail_detection_enabled = Column(Boolean, default=False) # 46
    voicemail_message = Column(Text, default="Hola, llamaba de Ubrokers. Le enviaré un WhatsApp.") # 47
    machine_detection_sensitivity = Column(Float, default=0.7) # 48
    # Phone
    voicemail_detection_enabled_phone = Column(Boolean, default=True)
    voicemail_message_phone = Column(Text, default="Hola, llamaba de Ubrokers. Le enviaré un WhatsApp.")
    machine_detection_sensitivity_phone = Column(Float, default=0.7)
    # Telnyx
    voicemail_detection_enabled_telnyx = Column(Boolean, default=True)
    voicemail_message_telnyx = Column(Text, default="Hola, llamaba de Ubrokers. Le enviaré un WhatsApp.")
    machine_detection_sensitivity_telnyx = Column(Float, default=0.7)

    # --- 3. PACING & NATURALNESS (50-52) ---
    # Base
    response_delay_seconds = Column(Float, default=0.5) # 50 (Artificial Delay)
    wait_for_greeting = Column(Boolean, default=True) # 51
    hyphenation_enabled = Column(Boolean, default=False) # 52
    end_call_phrases = Column(JSON, nullable=True) # 49 (Phrases to trigger hangup)
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
    # PHASE V: TELEPHONY TOOLS (Hardware & Compliance)
    # =============================================================================
    
    # --- 1. CREDENTIALS (BYOC - 53) ---
    # Phone (Twilio)
    twilio_account_sid = Column(String, nullable=True)
    twilio_auth_token = Column(String, nullable=True)
    twilio_from_number = Column(String, nullable=True) # 54 (Caller ID Phone)
    # Telnyx
    telnyx_api_key = Column(String, nullable=True)
    telnyx_api_user = Column(String, nullable=True)
    telnyx_connection_id = Column(String, nullable=True) # SIP ID
    
    # --- 2. INFRASTRUCTURE & SIP (54-57, 64) ---
    # Phone
    caller_id_phone = Column(String, nullable=True) # 54 Override
    sip_trunk_uri_phone = Column(String, nullable=True) # 55
    sip_auth_user_phone = Column(String, nullable=True) # 56
    sip_auth_pass_phone = Column(String, nullable=True)
    fallback_number_phone = Column(String, nullable=True) # 57
    geo_region_phone = Column(String, default="us-east-1") # 64
    # Telnyx
    caller_id_telnyx = Column(String, nullable=True)
    sip_trunk_uri_telnyx = Column(String, nullable=True)
    sip_auth_user_telnyx = Column(String, nullable=True)
    sip_auth_pass_telnyx = Column(String, nullable=True)
    fallback_number_telnyx = Column(String, nullable=True)
    geo_region_telnyx = Column(String, default="us-central")

    # --- 3. RECORDING & COMPLIANCE (58-59, 65) ---
    # Phone
    recording_enabled_phone = Column(Boolean, default=False) # 58
    recording_channels_phone = Column(String, default="mono") # 59 (mono/dual)
    hipaa_enabled_phone = Column(Boolean, default=False) # 65
    # Telnyx
    # recording_enabled_telnyx ALREADY EXISTS (line 376 - alias if needed)
    # reusing enable_recording_telnyx
    recording_channels_telnyx = Column(String, default="dual") 
    hipaa_enabled_telnyx = Column(Boolean, default=False)

    # --- 4. CALL FEATURES (60-63) ---
    # Phone
    transfer_type_phone = Column(String, default="cold") # 60/61 (cold/warm)
    dtmf_generation_enabled_phone = Column(Boolean, default=False) # 62
    dtmf_listening_enabled_phone = Column(Boolean, default=False) # 63
    # Telnyx
    transfer_type_telnyx = Column(String, default="cold")
    dtmf_generation_enabled_telnyx = Column(Boolean, default=False)
    dtmf_listening_enabled_telnyx = Column(Boolean, default=False)

    # --- 3. PACING & NATURALNESS (50-52) ---
    # Base
    response_delay_seconds = Column(Float, default=0.5) # 50 (Artificial Delay)
    wait_for_greeting = Column(Boolean, default=True) # 51
    hyphenation_enabled = Column(Boolean, default=False) # 52
    end_call_phrases = Column(JSON, nullable=True) # 49 (Phrases to trigger hangup)
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
    # PHASE VI: FUNCTION CALLING (Tools & Actions)
    # =============================================================================
    
    # --- 1. SERVER CONFIG (66-67, 70-71) ---
    # Base (Browser)
    tool_server_url = Column(String, nullable=True) # 66 (n8n Webhook)
    tool_server_secret = Column(String, nullable=True) # 67 (Auth Header)
    tool_timeout_ms = Column(Integer, default=5000) # 70
    tool_error_msg = Column(Text, default="Lo siento, hubo un error técnico.") # 71
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

    # --- 2. TOOL DEFINITIONS (68-69, 72) ---
    # Base
    tools_schema = Column(JSON, nullable=True) # 68 (Array of OpenAI Tools)
    async_tools = Column(Boolean, default=False) # 69 (Fire & Forget logic)
    client_tools_enabled = Column(Boolean, default=False) # 72 (Browser JS)
    # Phone
    tools_schema_phone = Column(JSON, nullable=True)
    async_tools_phone = Column(Boolean, default=False)
    # Telnyx
    tools_schema_telnyx = Column(JSON, nullable=True)
    async_tools_telnyx = Column(Boolean, default=False)

    # --- 3. SECURITY (73-75) ---
    # Base
    redact_params = Column(JSON, nullable=True) # 73 (List of keys to mask in logs)
    state_injection_enabled = Column(Boolean, default=False) # 74
    transfer_whitelist = Column(JSON, nullable=True) # 75 (List of allowed numbers)
    # Phone
    redact_params_phone = Column(JSON, nullable=True)
    state_injection_enabled_phone = Column(Boolean, default=False)
    transfer_whitelist_phone = Column(JSON, nullable=True)
    # Telnyx
    redact_params_telnyx = Column(JSON, nullable=True)
    state_injection_enabled_telnyx = Column(Boolean, default=False)
    transfer_whitelist_telnyx = Column(JSON, nullable=True)

    # =============================================================================
    # RATE LIMITING & PROVIDER LIMITS - Punto A3 Extensión (Configuración Dinámica)
    # =============================================================================
    # Rate Limiting por Endpoint (requests/minuto)
    rate_limit_global = Column(Integer, nullable=True, default=200)
    rate_limit_twilio = Column(Integer, nullable=True, default=30)
    rate_limit_telnyx = Column(Integer, nullable=True, default=50)
    rate_limit_websocket = Column(Integer, nullable=True, default=100)

    # Provider Limits (Límites de consumo por proveedor)
    limit_groq_tokens_per_min = Column(Integer, nullable=True, default=100000)
    limit_azure_requests_per_min = Column(Integer, nullable=True, default=100)
    limit_twilio_calls_per_hour = Column(Integer, nullable=True, default=100)
    limit_telnyx_calls_per_hour = Column(Integer, nullable=True, default=100)
    
    # =============================================================================
    # PHASE VII: ANALYSIS & DATA (Post-Call)
    # =============================================================================

    # --- 1. ANALYSIS & EXTRACTION (76-78) ---
    # Base
    analysis_prompt = Column(Text, nullable=True) # 76 (Instruction for summary)
    success_rubric = Column(Text, nullable=True) # 77 (Criteria for success)
    extraction_schema = Column(JSON, nullable=True) # 78 (JSON Schema for critical data)
    # Phone
    analysis_prompt_phone = Column(Text, nullable=True)
    success_rubric_phone = Column(Text, nullable=True)
    extraction_schema_phone = Column(JSON, nullable=True)
    # Telnyx
    analysis_prompt_telnyx = Column(Text, nullable=True)
    success_rubric_telnyx = Column(Text, nullable=True)
    extraction_schema_telnyx = Column(JSON, nullable=True)

    # --- 2. METRICS & FORMAT (79-81) ---
    # Base
    sentiment_analysis = Column(Boolean, default=False) # 79
    transcript_format = Column(String, default="text") # 80 (text, json, srt)
    cost_tracking_enabled = Column(Boolean, default=True) # 81
    # Phone
    sentiment_analysis_phone = Column(Boolean, default=False)
    transcript_format_phone = Column(String, default="text")
    cost_tracking_enabled_phone = Column(Boolean, default=True)
    # Telnyx
    sentiment_analysis_telnyx = Column(Boolean, default=False)
    transcript_format_telnyx = Column(String, default="text")
    cost_tracking_enabled_telnyx = Column(Boolean, default=True)

    # --- 3. OUTPUT & COMPLIANCE (82-85) ---
    # Base
    # webhook_url ALREADY EXISTS (line ~390) - Using it as "Webhook: End" (82)
    log_webhook_url = Column(String, nullable=True) # 83 (Streaming Logs)
    pii_redaction_enabled = Column(Boolean, default=False) # 84
    retention_days = Column(Integer, default=30) # 85
    # Phone
    webhook_url_phone = Column(String, nullable=True) # 82 specific
    webhook_secret_phone = Column(String, nullable=True)
    log_webhook_url_phone = Column(String, nullable=True)
    pii_redaction_enabled_phone = Column(Boolean, default=False)
    retention_days_phone = Column(Integer, default=30)
    # Telnyx
    webhook_url_telnyx = Column(String, nullable=True) # 82 specific
    webhook_secret_telnyx = Column(String, nullable=True)
    log_webhook_url_telnyx = Column(String, nullable=True)
    pii_redaction_enabled_telnyx = Column(Boolean, default=False)
    retention_days_telnyx = Column(Integer, default=30)

    # =============================================================================
    # PHASE VIII: SYSTEM & DEVOPS (Safe Controls)
    # =============================================================================
    
    # --- 1. GOVERNANCE & LIMITS (90-91, 98) ---
    concurrency_limit = Column(Integer, default=10) # 90
    spend_limit_daily = Column(Float, default=50.0) # 91 (USD)
    environment = Column(String, default="development") # 98 (dev/prod/staging)
    
    # --- 2. SECURITY & IDENTITY (89, 92-94, 100) ---
    custom_headers = Column(JSON, nullable=True) # 89 (Safe custom headers for webhooks)
    sub_account_id = Column(String, nullable=True) # 92 (Logical separation)
    # 93 API Keys handled via Auth table, config just needs logic flag? 
    # For now, simplistic string or JSON list of allowed keys for this agent
    allowed_api_keys = Column(JSON, nullable=True) # 93
    audit_log_enabled = Column(Boolean, default=True) # 94
    privacy_mode = Column(Boolean, default=False) # 100 (Do not train / Strict logs)
    
    # Phone/Telnyx Overrides for Privacy/Env
    environment_phone = Column(String, nullable=True)
    privacy_mode_phone = Column(Boolean, default=False)
    environment_telnyx = Column(String, nullable=True)
    privacy_mode_telnyx = Column(Boolean, default=False)
