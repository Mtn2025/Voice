"""Managers package - Modular components extracted from VoiceOrchestrator."""

from app.core.managers.audio_manager import AudioManager
from app.core.managers.crm_manager import CRMManager

__all__ = [
    "AudioManager",
    "CRMManager",
]
