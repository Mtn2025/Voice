"""
SSML Builder for Azure TTS
"""


class AzureSSMLBuilder:
    """
    Builds valid SSML for Azure TTS with prosody controls.

    Supports:
    - Prosody (rate, pitch, volume)
    - Emotional styles (mstts:express-as)
    - Style intensity (styledegree)
    """

    def __init__(self, voice_name: str, voice_language: str = "es-MX"):
        """
        Args:
            voice_name: Azure voice ID (e.g. "es-MX-DaliaNeural")
            voice_language: Language code (e.g. "es-MX")
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
        Builds complete SSML with prosody and emotional style controls.

        Args:
            text: Text to synthesize
            rate: Speed factor (0.5-2.0, default 1.0)
            pitch: Pitch change in semitones (-12 to +12, default 0)
            volume: Volume 0-100 (default 100)
            style: Optional emotional style (cheerful, empathetic, etc)
            style_degree: Style intensity (0.5-2.0, default 1.0)

        Returns:
            Valid SSML string for Azure TTS
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
    Helper function to build SSML quickly.

    Args:
        voice_name: Azure voice ID
        text: Text to synthesize
        **kwargs: rate, pitch, volume, style, style_degree

    Returns:
        Valid SSML string
    """
    builder = AzureSSMLBuilder(voice_name)
    return builder.build(text, **kwargs)
