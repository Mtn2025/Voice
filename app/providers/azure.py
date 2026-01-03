import azure.cognitiveservices.speech as speechsdk
from app.services.base import AbstractSTT, AbstractTTS
from app.core.config import settings
import logging

class AzureProvider(AbstractSTT, AbstractTTS):
    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY, 
            region=settings.AZURE_SPEECH_REGION
        )
        # Latency optimization
        # InitialSilence: Time to wait for user to START speaking
        # REMOVED hardcoded: self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
        # SegmentationSilence: Time of silence to consider the user has STOPPED speaking (Pause detection)
        # REMOVED hardcoded: self.speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "900")
        
    def get_available_voices(self):
        return [
            "es-MX-DaliaNeural",
            "es-MX-JorgeNeural",
            "es-MX-BeatrizNeural",
            "es-MX-CandelaNeural",
            "es-MX-CarlotaNeural",
            "es-MX-CecilioNeural",
            "es-MX-GerardoNeural",
            "es-MX-LarissaNeural",
            "es-MX-LibertoNeural",
            "es-MX-LucianoNeural",
            "es-MX-MarinaNeural",
            "es-MX-NurielNeural",
            "es-MX-PelayoNeural",
            "es-MX-RenataNeural",
            "es-MX-YagoNeural",
            "es-ES-ElviraNeural",
            "es-US-PalomaNeural",
            "en-US-JennyNeural"
        ]

    def get_voice_styles(self):
        """Returns a dict of voice_name -> list of styles"""
        return {
            "es-MX-DaliaNeural": ["customerservice", "chat", "cheerful", "calm", "sad", "angry", "fearful", "disgruntled", "serious", "affectionate", "gentle"],
            "es-MX-JorgeNeural": ["chat", "conversational", "customerservice", "cheerful", "empathetic", "serious"],
            "es-ES-ElviraNeural": ["customerservice", "empathetic", "cheerful", "calm", "chat"],
            "en-US-JennyNeural": ["assistant", "chat", "customerservice", "newscast", "angry", "cheerful", "sad", "excited", "friendly", "terrified", "shouting", "unfriendly", "whispering", "hopeful"]
        }

    def get_available_languages(self):
        return [
            "es-MX",
            "es-ES",
            "es-US",
            "es-AR",
            "es-CO",
            "es-CL",
            "en-US"
        ]

    def create_recognizer(self, language: str = "es-MX", audio_mode: str = "twilio", 
                          on_interruption_callback=None, event_loop=None,
                          initial_silence_ms: int = 5000,
                          segmentation_silence_ms: int = 1000):
        """
        audio_mode: 'twilio' (8khz mulaw) or 'browser' (16khz pcm)
        """
        self.speech_config.speech_recognition_language = language
        
        # Apply Timeouts Dynamically - Set to "Infinity" to let Orchestrator manage state
        # 1. InitialSilence: Time before user *starts* speaking (Default is often 5s). 
        #    If greeting is long, this kills the session. Azure soft limit is ~30s.
        self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, str(initial_silence_ms)) 
        # 2. EndSilence: Time after speech to consider "phrase" done. 
        #    We want short latency, but let's stick to the config if valid, else 1000ms.
        self.speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, str(segmentation_silence_ms))
        # 3. Connection Silence: Keepalive (REMOVED due to AttributeError)
        # self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_RecognitionEndpointVersion, "1")
        
        if audio_mode == "browser":
             format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
        else:
             # Manual Decode Mode: We decode MuLaw->PCM in Orchestrator before proper streaming
             # So we tell Azure this is PCM 16-bit 8kHz
             # Manual Decode Mode: We decode MuLaw->PCM in Orchestrator before proper streaming
             # So we tell Azure this is PCM 16-bit 8kHz
             format = speechsdk.audio.AudioStreamFormat(samples_per_second=8000, bits_per_sample=16, channels=1)
             import logging
             logging.warning(f"🎧 [AZURE PROVIDER] Created AudioStreamFormat: 8000Hz, 16bit, 1ch (Mode: {audio_mode})")

        push_stream = speechsdk.audio.PushAudioInputStream(stream_format=format)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, 
            audio_config=audio_config
        )
        self.recognizer = recognizer

        # Barge-in Sensitivity Logic
        if on_interruption_callback and event_loop:
            import asyncio
            def recognizing_cb(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
                    text = evt.result.text
                    if on_interruption_callback:
                        event_loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(on_interruption_callback(text))
                        )
            recognizer.recognizing.connect(recognizing_cb)

        return recognizer, push_stream

    def create_synthesizer(self, voice_name: str, audio_mode: str = "twilio"):
        self.speech_config.speech_synthesis_voice_name = voice_name
        
        if audio_mode == "browser":
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm)
        else:
            # Telephony Default (Twilio/Telnyx) -> Mu-Law 8kHz
            # This is the standard telephony format, removing need for custom transcoding in Orchestrator.
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw)
        
        # IMPORTANT: In Docker (headless), we must not use default speaker (audio_config=None)
        # causing Error 2176. We redirect to /dev/null to avoid hardware init.
        # The audio data is still returned in result.audio_data by speak_text_async.
        audio_config = speechsdk.audio.AudioConfig(filename="/dev/null")
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config, 
            audio_config=audio_config 
        )
        return synthesizer

    async def synthesize_stream(self, text: str):
        # Implementation left to orchestrator calling synthesizer directly for now, 
        # or we wraps speak_text_async here.
        pass
            
    async def stop_recognition(self):
        """
        Stop continuous recognition safely.
        """
        if self.recognizer:
            self.recognizer.stop_continuous_recognition_async()
            
    async def close(self):
        # ... logic to clean resources if needed ...
        pass
