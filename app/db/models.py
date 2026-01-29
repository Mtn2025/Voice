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
    # RATE LIMITING & PROVIDER LIMITS - Punto A3 Extensión (Configuración Dinámica)
    # =============================================================================
    # Rate Limiting por Endpoint (requests/minuto)
    # Estos valores permiten control dinámico sin editar código
    rate_limit_global = Column(Integer, nullable=True, default=200)
    rate_limit_twilio = Column(Integer, nullable=True, default=30)
    rate_limit_telnyx = Column(Integer, nullable=True, default=50)
    rate_limit_websocket = Column(Integer, nullable=True, default=100)

    # Provider Limits (Límites de consumo por proveedor)
    limit_groq_tokens_per_min = Column(Integer, nullable=True, default=100000)
    limit_azure_requests_per_min = Column(Integer, nullable=True, default=100)
    limit_twilio_calls_per_hour = Column(Integer, nullable=True, default=100)
    limit_telnyx_calls_per_hour = Column(Integer, nullable=True, default=100)
