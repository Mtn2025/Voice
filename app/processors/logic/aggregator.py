
import logging
import asyncio
from typing import Any, List, Dict

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame, CancelFrame
# from app.services.base import LLMProvider # Only if needed for typing

logger = logging.getLogger(__name__)

class ContextAggregator(FrameProcessor):
    """
    Aggregates User Transcripts into coherent Turns.
    Manages Conversation History.
    Triggers LLM only when "Turn" is complete (Smart Silence).
    """
    def __init__(self, config: Any, conversation_history: List[Dict]):
        super().__init__(name="ContextAggregator")
        self.config = config
        self.conversation_history = conversation_history
        
        # State
        self.interim_buffer = ""
        self.current_turn_text = ""
        self.user_speaking = False
        
        # Turn Management
        self.turn_timeout = 0.6 # Seconds to wait after speech stops
        self._turn_timer_task = None
        
        # Events
        self.response_required = asyncio.Event()

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, UserStartedSpeakingFrame):
                await self._handle_started_speaking()
                # Push downstream to pause TTS if needed
                await self.push_frame(frame, direction)
                
            elif isinstance(frame, UserStoppedSpeakingFrame):
                await self._handle_stopped_speaking()
                # Push downstream
                await self.push_frame(frame, direction)
                
            elif isinstance(frame, TextFrame):
                # Assume TextFrames from STT are FINAL unless marked otherwise
                # Azure Text is usually "recognized" (final).
                # If we had "recognizing" (interim), we would update buffer.
                # For now, treat as additive to current turn.
                await self._handle_text(frame.text)
                
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _handle_started_speaking(self):
        self.user_speaking = True
        # Cancel any pending turn completion
        if self._turn_timer_task:
            self._turn_timer_task.cancel()
            self._turn_timer_task = None
            
        # We might want to send a CancelFrame downstream to stop the bot!
        # This is the "Barge-in" mechanic.
        await self.push_frame(CancelFrame(reason="User Barge-In"))

    async def _handle_stopped_speaking(self):
        self.user_speaking = False
        # Start Turn Timer if we have text
        if self.current_turn_text:
            self._turn_timer_task = asyncio.create_task(self._monitor_turn_completion())

    async def _handle_text(self, text: str):
        if not text.strip():
            return
            
        # Append to current turn
        self.current_turn_text += " " + text
        
        # If user is NOT speaking (e.g. short utterance where VAD stopped before Text arrived),
        # we should start the timer.
        if not self.user_speaking:
             if self._turn_timer_task:
                 self._turn_timer_task.cancel()
             self._turn_timer_task = asyncio.create_task(self._monitor_turn_completion())

    async def _monitor_turn_completion(self):
        try:
            await asyncio.sleep(self.turn_timeout)
            # Timeout reached -> Turn Complete!
            await self._commit_turn()
        except asyncio.CancelledError:
            pass

    async def _commit_turn(self):
        text = self.current_turn_text.strip()
        if not text:
            return
            
        logger.info(f"✅ [TURN COMPLETE] User: {text}")
        
        # 1. Update History
        self.conversation_history.append({"role": "user", "content": text})
        
        # 2. Reset State
        self.current_turn_text = ""
        
        # 3. Create a Frame to trigger LLM
        # We need a new Frame type "LLMContextFrame" or just reuse TextFrame?
        # Actually, LLMProcessor receives TextFrames. 
        # But if we send `TextFrame(text=full_turn)`, LLMProcessor logic (if unchanged) 
        # will treat it as "User Input".
        # Which is what we want.
        
        # However, we must ensure LLMProcessor *knows* this is a Full Turn and not a fragment.
        # Our `LLMProcessor` currently does:
        #   process_frame(TextFrame) -> _handle_user_text -> Generate
        
        # So yes, pushing the aggregated text frame triggers the LLM.
        await self.push_frame(TextFrame(text=text, is_final=True))
