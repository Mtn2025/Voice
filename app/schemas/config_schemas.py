"""
Configuration Schemas for Dashboard [DEPRECATED]

⚠️ DEPRECATED: Este archivo está obsoleto.

**USAR EN SU LUGAR**:
- `app/schemas/browser_schemas.py` - Para perfil Browser/Simulador
- `app/schemas/twilio_schemas.py` - Para perfil Twilio/Phone
- `app/schemas/telnyx_schemas.py` - Para perfil Telnyx

Antiguo alcance: Browser+Twilio+Telnyx (todo mezclado) - INCORRECTO
**RAZÓN**: Separación hexagonal - cada perfil en su propio archivo.
Las clases BrowserConfigUpdate, TwilioConfigUpdate, y TelnyxConfigUpdate
se han movido a sus respectivos archivos para evitar cross-contamination.


Mantenido temporalmente solo para CoreConfigUpdate.
"""

from pydantic import BaseModel, Field


class CoreConfigUpdate(BaseModel):
    """
    Core/Global configuration.
    """
    stt_provider: str | None = Field(None, max_length=50, alias="sttProvider")
    llm_provider: str | None = Field(None, max_length=50, alias="llmProvider")
    tts_provider: str | None = Field(None, max_length=50, alias="voiceProvider")
    extraction_model: str | None = Field(None, max_length=100, alias="extractionModel")

    model_config = {"extra": "ignore", "populate_by_name": True}


# 🚫 NO AGREGAR MÁS CLASES AQUÍ
# Usar archivos separados por perfil siguiendo arquitectura hexagonal
