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
        self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
        
    def create_recognizer(self, language: str = "es-MX", audio_mode: str = "twilio"):
        """
        audio_mode: 'twilio' (8khz mulaw) or 'browser' (16khz pcm)
        """
        self.speech_config.speech_recognition_language = language
        
        if audio_mode == "browser":
             format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
        else:
             format = speechsdk.audio.AudioStreamFormat(samples_per_second=8000, bits_per_sample=8, channels=1, wave_stream_format=speechsdk.AudioStreamWaveFormat.MULAW)

        push_stream = speechsdk.audio.PushAudioInputStream(stream_format=format)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, 
            audio_config=audio_config
        )
        return recognizer, push_stream

    def create_synthesizer(self, voice_name: str, audio_mode: str = "twilio"):
        self.speech_config.speech_synthesis_voice_name = voice_name
        
        if audio_mode == "browser":
            self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm)
        else:
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
