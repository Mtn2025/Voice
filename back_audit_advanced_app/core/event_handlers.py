"""
Event handlers for Azure STT (Speech-to-Text) events.
Decouples event handling from orchestrator logic.
"""
import logging

import azure.cognitiveservices.speech as speechsdk


class AzureSTTHandlers:
    """
    Handlers for Azure Speech SDK events.
    Provides callbacks for recognition events.
    """

    def __init__(self, on_recognized_callback=None, on_canceled_callback=None):
        """
        Initialize STT event handlers.

        Args:
            on_recognized_callback: Function to call when text is recognized
            on_canceled_callback: Function to call on cancellation
        """
        self.on_recognized = on_recognized_callback
        self.on_canceled = on_canceled_callback
        self.logger = logging.getLogger(__name__)

    def handle_recognizing(self, evt: speechsdk.SpeechRecognitionEventArgs):
        """
        Handle intermediate recognition results.

        Args:
            evt: Speech recognition event
        """
        # Typically not used (we only care about final results)
        pass

    def handle_recognized(self, evt: speechsdk.SpeechRecognitionEventArgs):
        """
        Handle final recognition result.

        Args:
            evt: Speech recognition event with final text
        """
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text = evt.result.text

            if text and self.on_recognized:
                # Call the callback with recognized text
                self.on_recognized(text, evt)

        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            self.logger.debug("No speech recognized (silence or noise)")

    def handle_canceled(self, evt: speechsdk.SpeechRecognitionCanceledEventArgs):
        """
        Handle recognition cancellation.

        Args:
            evt: Cancellation event
        """
        self.logger.warning(f"Recognition canceled: {evt.reason}")

        if evt.reason == speechsdk.CancellationReason.Error:
            self.logger.error(f"Error details: {evt.error_details}")

            if self.on_canceled:
                self.on_canceled(evt)

    def handle_session_stopped(self, evt: speechsdk.SessionEventArgs):
        """
        Handle session stop.

        Args:
            evt: Session event
        """
        self.logger.info("STT session stopped")

    def handle_session_started(self, evt: speechsdk.SessionEventArgs):
        """
        Handle session start.

        Args:
            evt: Session event
        """
        self.logger.info("STT session started")
