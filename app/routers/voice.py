"""
Voice preview and TTS testing endpoints.
Modularized from dashboard.py as part of post-audit refactoring.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.auth_simple import verify_api_key
from app.providers.azure import AzureProvider

router = APIRouter(prefix="/api/voice", tags=["voice"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("/preview", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def preview_voice(request: Request):
    """
    Voice preview endpoint for testing TTS with custom text.
    Returns audio data or error.
    """
    try:
        data = await request.json()
        text = data.get("text", "Hola, esta es una prueba de voz.")
        voice_name = data.get("voiceId", "es-MX-DaliaNeural")
        voice_style = data.get("voiceStyle", "Default")
        voice_speed = float(data.get("voiceSpeed", 1.0))
        voice_pitch = float(data.get("voicePitch", 0.0))
        voice_volume = float(data.get("voiceVolume", 100.0))
        
        logger.info(f"🎙️ Voice preview: {voice_name} | {text[:30]}...")
        
        # Initialize Azure TTS
        azure_provider = AzureProvider()
        
        # Build SSML
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
               xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-MX">
            <voice name="{voice_name}">
                <mstts:express-as style="{voice_style}">
                    <prosody rate="{voice_speed}" pitch="{voice_pitch:+.0f}Hz" volume="{voice_volume}">
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        
        # Synthesize
        audio_data = await azure_provider.synthesize_ssml(ssml)
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to synthesize voice")
        
        # Return base64 audio
        import base64
        return {
            "status": "success",
            "audio": base64.b64encode(audio_data).decode()
        }
    
    except Exception as e:
        logger.error(f"❌ Voice preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
