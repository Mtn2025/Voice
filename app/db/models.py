from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    extracted_data = Column(JSON, nullable=True) # New
    
    transcripts = relationship("Transcript", back_populates="call")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"))
    role = Column(String) # user or assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    call = relationship("Call", back_populates="transcripts")

class AgentConfig(Base):
    __tablename__ = "agent_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, default="default")
    
    # Providers
    stt_provider = Column(String, default="azure")
    stt_language = Column(String, default="es-MX") # Add stt_language
    llm_provider = Column(String, default="groq")
    llm_model = Column(String, default="llama-3.3-70b-versatile") 
    extraction_model = Column(String, default="llama-3.1-8b-instant")
    interruption_threshold = Column(Integer, default=5) # Noise Tolerance
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
- Concisión: MÁXIMO 2 oraciones por turno. Habla como si fuera una llamada real.
- Muletillas permitidas: "Claro", "Entiendo", "Le comento".
</style>

<phases>
1. **CONEXIÓN**: Confirmar que hablas con el dueño/encargado.
   - *Si no es el dueño*: Pregunta cuándo podrías localizarlo o si hay alguien más a cargo.
   - *Si es el dueño*: Avanza a CALIFICACIÓN.

2. **CALIFICACIÓN**: Despertar interés con el "Informe Fiscal 2026".
   - Pregunta: "¿Ya recibió la actualización sobre beneficios fiscales para socios de la cámara?"
   - Si dice SÍ: "Excelente. ¿Ya están aplicando los fondos de ahorro deducibles?"
   - Si dice NO: "Le comento, hay nuevos esquemas de ahorro 100% deducibles..." -> Avanza a PROPUESTA.

3. **PROPUESTA**: Ofrecer la consultoría gratuita (Call to Action).
   - "Mi especialista puede explicarle en una llamada de 15 minutos cómo aplicar esto. Es sin costo."

4. **CONVERSIÓN (CIERRE)**: Obtener WhatsApp/Agenda.
   - "¿Le parece bien si le envío la info a su WhatsApp para coordinar?"
   - Obtener Nombre y Teléfono.
</phases>

<rules>
- SI EL USUARIO SE DESVÍA: Responde brevemente y regresa amablemente a la FASE actual.
- SI PIDE PRECIO: "Es un beneficio gratuito para empresas registradas."
- SI NO LE INTERESA: "Entiendo, gracias por su tiempo." (Corta cortésmente).
</rules>""")
    voice_name = Column(String, default="es-MX-DaliaNeural")
    voice_style = Column(String, nullable=True) # New: Style/Emotion
    voice_speed = Column(Float, default=1.0)
    temperature = Column(Float, default=0.7)
    background_sound = Column(String, default="none") # none, office, cafe, call_center
    
    # Flow Control
    idle_timeout = Column(Float, default=10.0) # Seconds to wait before prompt
    idle_message = Column(String, default="¿Hola? ¿Sigue ahí?")
    max_duration = Column(Integer, default=600) # Max call seconds
    
    # VAPI Stage 1: Model & Voice
    first_message = Column(String, default="Hola, soy Andrea de Ubrokers. ¿Me escucha bien?")
    first_message_mode = Column(String, default="speak-first") # speak-first, wait-for-user, speak-first-dynamic
    max_tokens = Column(Integer, default=250)
    
    voice_id_manual = Column(String, nullable=True) # Override standard list
    background_sound_url = Column(String, nullable=True) # External URL for ambient noise
    input_min_characters = Column(Integer, default=3)
    punctuation_boundaries = Column(String, nullable=True)
    
    # VAPI Stage 2: Transcriber & Functions
    silence_timeout_ms = Column(Integer, default=500) # Speech end silence
    segmentation_max_time = Column(Integer, default=30000) # ms (max phrase duration)
    segmentation_strategy = Column(String, default="default") # default, time, semantic
    enable_denoising = Column(Boolean, default=True)
    
    enable_end_call = Column(Boolean, default=True)
    enable_dial_keypad = Column(Boolean, default=False)
    transfer_phone_number = Column(String, nullable=True)
    
    # Flow Control (Legacy/Simple)
    idle_timeout = Column(Float, default=10.0) 
    idle_message = Column(String, default="¿Hola? ¿Sigue ahí?")
    max_duration = Column(Integer, default=600)
    
    is_active = Column(Boolean, default=True)
