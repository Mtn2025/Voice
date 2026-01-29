"""
SSML Builder for Azure TTS
Professional, clean, reusable implementation
"""


class AzureSSMLBuilder:
    """
    Construye SSML válido para Azure TTS con controles de prosody.
    
    Soporta:
    - Prosody (rate, pitch, volume)
    - Emotional styles (mstts:express-as)
    - Style intensity (styledegree)
    """
    
    def __init__(self, voice_name: str, voice_language: str = "es-MX"):
        """
        Args:
            voice_name: Azure voice ID (ej. "es-MX-DaliaNeural")
            voice_language: Language code (ej. "es-MX")
        """
        self.voice_name = voice_name
        self.voice_language = voice_language
        self.xmlns = "http://www.w3.org/2001/10/synthesis"
        self.xmlns_mstts = "http://www.w3.org/2001/mstts"
    
    def build(
        self,
        text: str,
        rate: float = 1.0,
        pitch: int = 0,
        volume: int = 100,
        style: str | None = None,
        style_degree: float = 1.0
    ) -> str:
        """
        Construye SSML completo con controles de prosody y estilo emocional.
        
        Args:
            text: Texto a sintetizar
            rate: Factor velocidad (0.5-2.0, default 1.0)
            pitch: Cambio tono en semitones (-12 a +12, default 0)
            volume: Volumen 0-100 (default 100)
            style: Estilo emocional opcional (cheerful, empathetic, etc)
            style_degree: Intensidad del estilo (0.5-2.0, default 1.0)
            
        Returns:
            SSML string válido para Azure TTS
        """
        # Convert parameters to SSML format
        rate_str = f"{rate}"
        pitch_str = f"{pitch:+d}st" if pitch != 0 else "default"
        volume_str = f"{volume}"
        
        # Build SSML components
        parts = []
        
        # SSML header
        parts.append(
            f'<speak version="1.0" '
            f'xmlns="{self.xmlns}" '
            f'xmlns:mstts="{self.xmlns_mstts}" '
            f'xml:lang="{self.voice_language}">'
        )
        
        # Voice element
        parts.append(f'<voice name="{self.voice_name}">')
        
        # Emotional style wrapper (optional)
        if style and style.strip():
            parts.append(
                f'<mstts:express-as style="{style}" styledegree="{style_degree}">'
            )
        
        # Prosody controls (always applied)
        parts.append(
            f'<prosody rate="{rate_str}" pitch="{pitch_str}" volume="{volume_str}">'
        )
        
        # Escaped text content
        parts.append(self._escape_xml(text))
        
        # Close prosody
        parts.append('</prosody>')
        
        # Close style if it was opened
        if style and style.strip():
            parts.append('</mstts:express-as>')
        
        # Close voice and speak
        parts.append('</voice>')
        parts.append('</speak>')
        
        return ''.join(parts)
    
    @staticmethod
    def _escape_xml(text: str) -> str:
        """
        Escape XML special characters to prevent SSML errors.
        
        Args:
            text: Raw text string
            
        Returns:
            XML-safe string
        """
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;')
        )


def build_azure_ssml(voice_name: str, text: str, **kwargs) -> str:
    """
    Helper function para construir SSML rápidamente.
    
    Args:
        voice_name: Azure voice ID
        text: Texto a sintetizar
        **kwargs: rate, pitch, volume, style, style_degree
        
    Returns:
        SSML string válido
        
    Example:
        ssml = build_azure_ssml(
            "es-MX-DaliaNeural",
            "Hola, ¿cómo estás?",
            rate=1.0,
            pitch=2,
            volume=90,
            style="cheerful",
            style_degree=1.3
        )
    """
    builder = AzureSSMLBuilder(voice_name)
    return builder.build(text, **kwargs)
