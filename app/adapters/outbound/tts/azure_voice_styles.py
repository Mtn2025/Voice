"""
Azure TTS Voice Styles - Mapeo Oficial con Traducciones al Español

Fuente: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts
Última actualización: 2026-02-09

Este archivo contiene el mapeo COMPLETO de estilos emocionales soportados por Azure TTS
para voces en español (México, US, España) según documentación oficial de Microsoft.
"""

# =============================================================================
# TRADUCCIONES DE ESTILOS EMOCIONALES (Inglés → Español)
# =============================================================================

STYLE_TRANSLATIONS = {
    # Emociones Básicas
    "angry": "Enojado",
    "sad": "Triste",
    "cheerful": "Alegre",
    "excited": "Emocionado",
    "fearful": "Temeroso",
    
    # Estados de Ánimo
    "calm": "Calmado",
    "gentle": "Gentil",
    "friendly": "Amigable",
    "hopeful": "Esperanzado",
    "unfriendly": "Poco Amigable",
    "terrified": "Aterrorizado",
    
    # Contextos Profesionales
    "assistant": "Asistente",
    "chat": "Conversación",
    "customerservice": "Servicio al Cliente",
    "newscast": "Noticiero",
    "newscast-casual": "Noticiero Casual",
    "newscast-formal": "Noticiero Formal",
    
    # Intensidad / Volumen
    "shouting": "Gritando",
    "whispering": "Susurrando",
    
    # Otros Contextos
    "empathetic": "Empático",
    "disgruntled": "Descontento",
    "embarrassed": "Avergonzado",
    "affectionate": "Af ectuoso",
    "serious": "Serio",
    "narration-professional": "Narración Profesional",
}

# =============================================================================
# MAPEO OFICIAL DE ESTILOS POR VOZ (es-MX, es-US, es-ES)
# =============================================================================

VOICE_STYLES_OFFICIAL = {
    # ========== ESPAÑOL (MÉXICO) - es-MX ========== #
    
    "es-MX-DaliaNeural": {
        "styles": ["cheerful", "sad", "whispering"],
        "styles_es": ["Alegre", "Triste", "Susurrando"]
    },
    
    "es-MX-JorgeNeural": {
        "styles": ["chat", "cheerful", "excited", "sad", "whispering"],
        "styles_es": ["Conversación", "Alegre", "Emocionado", "Triste", "Susurrando"]
    },
    
    # Nota: Otras voces es-MX (Beatriz, Candela, Carlota, etc.) NO tienen estilos según docs oficiales
    
    # ========== ESPAÑOL (ESTADOS UNIDOS) - es-US ========== #
    
    # Nota: Según documentación oficial de Microsoft (2024-2026), las voces es-US
    # NO tienen estilos emocionales documentados. Solo voces es-MX y es-ES tienen soporte.
    
    # ========== ESPAÑOL (ESPAÑA) - es-ES ========== #
    
    "es-ES-AlvaroNeural": {
        "styles": ["cheerful", "sad"],
        "styles_es": ["Alegre", "Triste"]
    },
    
    # Nota: Otras voces es-ES NO tienen estilos según docs oficiales
    
    # ========== VOCES SIN ESTILOS (Default/None) ========== #
    "default": {
        "styles": [],
        "styles_es": []
    }
}

# =============================================================================
# FUNCIÓN HELPER: Obtener Estilos en Español
# =============================================================================

def get_voice_styles_spanish(voice_id: str) -> list[dict[str, str]]:
    """
    Retorna lista de estilos emocionales en español para una voz específica.
    
    Args:
        voice_id: ID de la voz (ej: "es-MX-DaliaNeural")
    
    Returns:
        Lista de dicts con {id: str, label: str}
        Ejemplo: [{"id": "cheerful", "label": "Alegre"}, ...]
    
    Ejemplos:
        >>> get_voice_styles_spanish("es-MX-DaliaNeural")
        [
            {"id": "cheerful", "label": "Alegre"},
            {"id": "sad", "label": "Triste"},
            {"id": "whispering", "label": "Susurrando"}
        ]
        
        >>> get_voice_styles_spanish("es-MX-BeatrizNeural")
        []  # No tiene estilos
    """
    voice_data = VOICE_STYLES_OFFICIAL.get(voice_id, VOICE_STYLES_OFFICIAL["default"])
    
    styles_en = voice_data.get("styles", [])
    styles_es = voice_data.get("styles_es", [])
    
    # Construir lista de dicts
    result = []
    for i, style_id in enumerate(styles_en):
        result.append({
            "id": style_id,  # Valor técnico que se envía a API
            "label": styles_es[i] if i < len(styles_es) else style_id.title()  # Labels para UI
        })
    
    return result


def get_all_voice_styles_spanish() -> dict[str, list[dict[str, str]]]:
    """
    Retorna mapeo completo de TODAS las voces con estilos en español.
    
    Returns:
        Dict con {voice_id: [{"id": str, "label": str}, ...]}
    
    Ejemplo:
        >>> get_all_voice_styles_spanish()
        {
            "es-MX-DaliaNeural": [
                {"id": "cheerful", "label": "Alegre"},
                {"id": "sad", "label": "Triste"},
                {"id": "whispering", "label": "Susurrando"}
            ],
            "es-MX-JorgeNeural": [
                {"id": "chat", "label": "Conversación"},
                ...
            ],
            ...
        }
    """
    result = {}
    
    for voice_id in VOICE_STYLES_OFFICIAL.keys():
        if voice_id == "default":
            continue
        result[voice_id] = get_voice_styles_spanish(voice_id)
    
    # Agregar entrada default para voces sin estilos
    result["default"] = []
    
    return result


# =============================================================================
# VALIDACIÓN: Voces Disponibles en es-MX, es-US, es-ES (Feb 2026)
# =============================================================================

AVAILABLE_VOICES = {
    "es-MX": [
        "es-MX-BeatrizNeural",
        "es-MX-CandelaNeural",
        "es-MX-CarlotaNeural",
        "es-MX-CecilioNeural",
        "es-MX-DaliaNeural",      # ✅ Tiene estilos
        "es-MX-GerardoNeural",
        "es-MX-JorgeNeural",       # ✅ Tiene estilos
        "es-MX-LarissaNeural",
        "es-MX-LibertoNeural",
        "es-MX-LucianoNeural",
        "es-MX-MarinaNeural",
        "es-MX-NuriaNeural",
        "es-MX-PelayoNeural",
        "es-MX-RenataNeural",
        "es-MX-YagoNeural",
    ],
    "es-US": [
        "es-US-AlonsoNeural",
        "es-US-PalomaNeural",
        # Nota: NO tienen estilos emocionales según docs oficiales
    ],
    "es-ES": [
        "es-ES-AlvaroNeural",      # ✅ Tiene estilos
        "es-ES-ElviraNeural",
        # ... más voces sin estilos
    ]
}

# =============================================================================
# RESUMEN DE HALLAZGOS
# =============================================================================

"""
HALLAZGOS CLAVE (Basado en Documentación Oficial Microsoft 2024-2026):

1. **Voces ES-MX con Estilos:**
   - DaliaNeural: 3 estilos (cheerful, sad, whispering)
   - JorgeNeural: 5 estilos (chat, cheerful, excited, sad, whispering)
   - TOTAL: Solo 2 de 15 voces tienen estilos

2. **Voces ES-US:**
   - NO documentan estilos emocionales
   - API puede retornar lista vacía

3. **Voces ES-ES:**
   - AlvaroNeural: 2 estilos (cheerful, sad)
   - Resto sin estilos

4. **Implementación Actual:**
   - ✅ Campo UI se oculta correctamente con `x-show="availableStyles.length > 0"`
   - ❌ Estilos están en INGLÉS (necesitan traducción)
   - ✅ Lógica de cache funciona correctamente

5. **Acciones Requeridas:**
   - Actualizar azure_tts_adapter.py para retornar estilos en español
   - Verificar que UI muestra/oculta campo correctamente
   - Agregar traducciones de estilos
"""
