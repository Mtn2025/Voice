from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean
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
    llm_provider = Column(String, default="groq")
    tts_provider = Column(String, default="azure")
    
    # Parameters
    system_prompt = Column(Text, default="Eres Andrea, una asistente útil y amable. Responde brevemente y en español de México.")
    voice_name = Column(String, default="es-MX-DaliaNeural")
    voice_speed = Column(Float, default=1.0)
    temperature = Column(Float, default=0.7)
    
    is_active = Column(Boolean, default=True)
