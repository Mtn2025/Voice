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

    "es-MX-BeatrizNeural": {"styles": [], "styles_es": []},
    "es-MX-CandelaNeural": {"styles": [], "styles_es": []},
    "es-MX-CarlotaNeural": {"styles": [], "styles_es": []},
    "es-MX-CecilioNeural": {"styles": [], "styles_es": []},
    "es-MX-GerardoNeural": {"styles": [], "styles_es": []},
    "es-MX-LarissaNeural": {"styles": [], "styles_es": []},
    "es-MX-LibertoNeural": {"styles": [], "styles_es": []},
    "es-MX-LucianoNeural": {"styles": [], "styles_es": []},
    "es-MX-MarinaNeural": {"styles": [], "styles_es": []},
    "es-MX-NuriaNeural": {"styles": [], "styles_es": []},
    "es-MX-PelayoNeural": {"styles": [], "styles_es": []},
    "es-MX-RenataNeural": {"styles": [], "styles_es": []},
    "es-MX-YagoNeural": {"styles": [], "styles_es": []},
    
    
    # ========== ESPAÑOL (ESTADOS UNIDOS) - es-US ========== #
    
    "es-US-AlonsoNeural": {"styles": [], "styles_es": []},
    "es-US-PalomaNeural": {"styles": [], "styles_es": []},
    
    # ========== ESPAÑOL (ESPAÑA) - es-ES ========== #
    
    "es-ES-AlvaroNeural": {
        "styles": ["cheerful", "sad"],
        "styles_es": ["Alegre", "Triste"]
    },
    
    "es-ES-ElviraNeural": {"styles": [], "styles_es": []},
    "es-ES-AbrilNeural": {"styles": [], "styles_es": []},
    "es-ES-ArnauNeural": {"styles": [], "styles_es": []},
    "es-ES-DarioNeural": {"styles": [], "styles_es": []},
    "es-ES-EliasNeural": {"styles": [], "styles_es": []},
    "es-ES-EstrellaNeural": {"styles": [], "styles_es": []},
    "es-ES-IreneNeural": {"styles": [], "styles_es": []},
    "es-ES-LaiaNeural": {"styles": [], "styles_es": []},
    "es-ES-LiaNeural": {"styles": [], "styles_es": []},
    "es-ES-NilNeural": {"styles": [], "styles_es": []},
    "es-ES-SaulNeural": {"styles": [], "styles_es": []},
    "es-ES-TeoNeural": {"styles": [], "styles_es": []},
    "es-ES-TrianaNeural": {"styles": [], "styles_es": []},
    "es-ES-VeraNeural": {"styles": [], "styles_es": []},
    
    # ========== INGLÉS (ESTADOS UNIDOS) - en-US ========== #
    
    "en-US-AriaNeural": {
        "styles": ["chat", "customerservice", "empathetic", "excited", "friendly", "hopeful", "narration-professional", "newscast-casual", "newscast-formal", "sad", "shouting", "terrified", "unfriendly", "whispering"],
        "styles_es": ["Conversación", "Servicio al Cliente", "Empático", "Emocionado", "Amigable", "Esperanzado", "Narración Profesional", "Noticiero Casual", "Noticiero Formal", "Triste", "Gritando", "Aterrorizado", "Poco Amigable", "Susurrando"]
    },
    
    "en-US-DavisNeural": {
        "styles": ["chat", "angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
        "styles_es": ["Conversación", "Enojado", "Alegre", "Emocionado", "Amigable", "Esperanzado", "Triste", "Gritando", "Aterrorizado", "Poco Amigable", "Susurrando"]
    },
    
    "en-US-GuyNeural": {
        "styles": ["newscast", "angry", "cheerful", "sad", "excited", "friendly", "terrified", "shouting", "whispering", "hopeful", "unfriendly"],
        "styles_es": ["Noticiero", "Enojado", "Alegre", "Triste", "Emocionado", "Amigable", "Aterrorizado", "Gritando", "Susurrando", "Esperanzado", "Poco Amigable"]
    },
    
    "en-US-JennyNeural": {
        "styles": ["assistant", "chat", "customerservice", "newscast", "angry", "cheerful", "sad", "excited", "friendly", "terrified", "shouting", "whispering", "hopeful", "unfriendly"],
        "styles_es": ["Asistente", "Conversación", "Servicio al Cliente", "Noticiero", "Enojado", "Alegre", "Triste", "Emocionado", "Amigable", "Aterrorizado", "Gritando", "Susurrando", "Esperanzado", "Poco Amigable"]
    },
    
    "en-US-JasonNeural": {
        "styles": ["angry", "cheerful", "sad", "excited", "friendly", "terrified", "shouting", "whispering", "hopeful", "unfriendly"],
        "styles_es": ["Enojado", "Alegre", "Triste", "Emocionado", "Amigable", "Aterrorizado", "Gritando", "Susurrando", "Esperanzado", "Poco Amigable"]
    },
    
    "en-US-NancyNeural": {
        "styles": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
        "styles_es": ["Enojado", "Alegre", "Emocionado", "Amigable", "Esperanzado", "Triste", "Gritando", "Aterrorizado", "Poco Amigable", "Susurrando"]
    },
    
    "en-US-SaraNeural": {
        "styles": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
        "styles_es": ["Enojado", "Alegre", "Emocionado", "Amigable", "Esperanzado", "Triste", "Gritando", "Aterrorizado", "Poco Amigable", "Susurrando"]
    },
    
    "en-US-TonyNeural": {
        "styles": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
        "styles_es": ["Enojado", "Alegre", "Emocionado", "Amigable", "Esperanzado", "Triste", "Gritando", "Aterrorizado", "Poco Amigable", "Susurrando"]
    },
    
    "en-US-JaneNeural": {
        "styles": ["angry", "cheerful", "excited", "friendly", "hopeful", "sad", "shouting", "terrified", "unfriendly", "whispering"],
        "styles_es": ["Enojado", "Alegre", "Emocionado", "Amigable", "Esperanzado", "Triste", "Gritando", "Aterrorizado", "Poco Amigable", "Susurrando"]
    },
    
    "en-US-AmberNeural": {"styles": [], "styles_es": []},
    "en-US-AnaNeural": {"styles": [], "styles_es": []},
    "en-US-AshleyNeural": {"styles": [], "styles_es": []},
    "en-US-BrandonNeural": {"styles": [], "styles_es": []},
    "en-US-ChristopherNeural": {"styles": [], "styles_es": []},
    "en-US-CoraNeural": {"styles": [], "styles_es": []},
    "en-US-ElizabethNeural": {"styles": [], "styles_es": []},
    "en-US-EricNeural": {"styles": [], "styles_es": []},
    "en-US-JacobNeural": {"styles": [], "styles_es": []},
    "en-US-MichelleNeural": {"styles": [], "styles_es": []},
    "en-US-MonicaNeural": {"styles": [], "styles_es": []},
    "en-US-RogerNeural": {"styles": [], "styles_es": []},
    "en-US-SteffanNeural": {"styles": [], "styles_es": []},
    "en-US-BlueNeural": {"styles": [], "styles_es": []},
    
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
    """
    # 1. Buscar en mapa oficial
    voice_data = VOICE_STYLES_OFFICIAL.get(voice_id)
    
    # 2. Si no existe en mapa, intentar obtener el default
    if not voice_data:
        voice_data = VOICE_STYLES_OFFICIAL["default"]
    
    styles_en = voice_data.get("styles", [])
    styles_es = voice_data.get("styles_es", [])
    
    # Construir lista de dicts
    result = []
    for i, style_id in enumerate(styles_en):
        translated_label = styles_es[i] if i < len(styles_es) else STYLE_TRANSLATIONS.get(style_id, style_id.title())
        result.append({
            "id": style_id,  # Valor técnico
            "label": translated_label # Label traducido
        })
    
    return result


def translate_style_list(api_styles: list[str]) -> list[dict[str, str]]:
    """
    Traduce una lista dinámica de estilos (desde API Azure) al español.
    
    Args:
        api_styles: Lista de strings de estilos en inglés (ej: ["cheerful", "sad"])
        
    Returns:
        Lista de dicts para UI: [{"id": "cheerful", "label": "Alegre"}, ...]
    """
    result = []
    # Deduplicate and sort
    sorted_styles = sorted(list(set(api_styles)))
    
    for style_id in sorted_styles:
        if not style_id or not style_id.strip():
            continue

        # 0. Filter out trivial/default styles that shouldn't trigger UI
        s_lower = style_id.lower()
        if s_lower in ["default", "general", "standard", "none"]:
            continue

        # 1. Try strict dictionary lookup
        label = STYLE_TRANSLATIONS.get(s_lower)
        
        # 2. Heuristic fallback (if new style appears in API)
        if not label:
            label = style_id.replace("-", " ").title()
            
        result.append({
            "id": style_id,
            "label": label
        })
        
    return result


def get_all_voice_styles_spanish() -> dict[str, list[dict[str, str]]]:
    """
    Retorna mapeo completo de TODAS las voces con estilos en español.
    """
    result = {}
    
    for voice_id in VOICE_STYLES_OFFICIAL.keys():
        if voice_id == "default":
            continue
        result[voice_id] = get_voice_styles_spanish(voice_id)
    
    # Agregar entrada default
    result["default"] = []
    
    return result


# =============================================================================
# VALIDACIÓN: Voces Disponibles en es-MX, es-US, en-US (Feb 2026)
# =============================================================================

AVAILABLE_VOICES = {
    "es-MX": [
        "es-MX-DaliaNeural",      # ✅ Tiene estilos
        "es-MX-JorgeNeural",       # ✅ Tiene estilos
        "es-MX-BeatrizNeural",
        "es-MX-CandelaNeural",
        "es-MX-CarlotaNeural",
        "es-MX-CecilioNeural",
        "es-MX-GerardoNeural",
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
    ],
    "en-US": [
        "en-US-AriaNeural",       # ✅ Tiene estilos
        "en-US-DavisNeural",      # ✅ Tiene estilos
        "en-US-GuyNeural",        # ✅ Tiene estilos
        "en-US-JennyNeural",      # ✅ Tiene estilos
        "en-US-JasonNeural",      # ✅ Tiene estilos
        "en-US-NancyNeural",      # ✅ Tiene estilos
        "en-US-SaraNeural",       # ✅ Tiene estilos
        "en-US-TonyNeural",       # ✅ Tiene estilos
        "en-US-JaneNeural",       # ✅ Tiene estilos
        "en-US-AmberNeural", "en-US-AnaNeural", "en-US-AshleyNeural",
        "en-US-BrandonNeural", "en-US-ChristopherNeural", "en-US-CoraNeural",
        "en-US-ElizabethNeural", "en-US-EricNeural", "en-US-JacobNeural",
        "en-US-MichelleNeural", "en-US-MonicaNeural", "en-US-RogerNeural",
        "en-US-SteffanNeural"
    ]
}

# =============================================================================
# RESUMEN DE HALLAZGOS (Update Feb-2026)
# =============================================================================

"""
HALLAZGOS CLAVE:

1. **Voces ES-MX con Estilos:**
   - Dalia, Jorge.

2. **Voces ES-US:**
   - Sin estilos soportados.

3. **Voces EN-US (Inglés):**
   - Soporte amplio de estilos (Jenny, Guy, Aria, etc).
   - Traducciones al ESPAÑOL agregadas para compliance con UI.

4. **Traducciones:**
   - Mapeo completo de estilos en inglés a etiquetas en español.
"""
