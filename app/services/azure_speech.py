import azure.cognitiveservices.speech as speechsdk
from app.core.config import settings
import logging

class AzureSpeechService:
    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY, 
            region=settings.AZURE_SPEECH_REGION
        )
        self.speech_config.speech_recognition_language = "es-MX"
        self.speech_config.speech_synthesis_voice_name = "es-MX-DaliaNeural" # Example Neural voice
        
        # Optimize for low latency
        self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
        
    def create_push_stream_recognizer(self, on_interruption_callback=None, event_loop=None):
        """
        Creates a recognizer that accepts a push stream (for incoming audio).
        Returns: (recognizer, push_stream)
        """
        # Twilio sends 8kHz mulaw
        format = speechsdk.audio.AudioStreamFormat(samples_per_second=8000, bits_per_sample=8, channels=1, wave_stream_format=speechsdk.AudioStreamWaveFormat.MULAW)
        push_stream = speechsdk.audio.PushAudioInputStream(stream_format=format)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, 
            audio_config=audio_config
        )

        # Define the recognizing callback locally to capture on_interruption_callback and event_loop
        if on_interruption_callback and event_loop:
            import asyncio # Import asyncio if not already at the top

            def recognizing_cb(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
                    # logging.info(f"Speech recognizing: {evt.result.text}")
                    text = evt.result.text
                    if on_interruption_callback:
                        # Pass text to handler for sensitivity logic
                        # Use event_loop.call_soon_threadsafe to schedule the async task
                        event_loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(on_interruption_callback(text))
                        )
            recognizer.recognizing.connect(recognizing_cb)

        return recognizer, push_stream

    def create_synthesizer(self):
        """
        Creates a speech synthesizer for TTS.
        We will use PullAudioOutputStream or just get bytes directly for streaming back to Twilio.
        For simplicity in the orchestrator, we might just get audio data events.
        """
        # We output 8kHz mulaw to match Twilio without transcoding
        self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw)
        
        # Null output because we want to intercept the stream, not play on server speakers
        audio_config = speechsdk.audio.AudioConfig(device_name=None)
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config, 
            audio_config=None # No audio output hardware
        )
        return synthesizer

azure_service = AzureSpeechService()
