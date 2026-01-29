
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
    def __init__(self, config: Any, conversation_history: List[Dict], llm_provider: Any = None):
        super().__init__(name="ContextAggregator")
        self.config = config
        self.conversation_history = conversation_history
        self.llm_provider = llm_provider
        
        # State
        self.interim_buffer = ""
        self.current_turn_text = ""
        self.user_speaking = False
        
        # Turn Management
        self.turn_timeout = 0.6 # Initial wait
        self.semantic_timeout = 1.2 # Extended wait if incomplete
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
        # this is the "Barge-in" mechanic.
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
            # 1. Wait initial short timeout (e.g. 0.6s)
            await asyncio.sleep(self.turn_timeout)
            
            # 2. Semantic Check (if enabled and provider available)
            # Only check if text is long enough to be ambiguous AND strategy is semantic
            strategy = getattr(self.config, 'segmentation_strategy', 'default')
            
            if strategy == 'semantic' and self.llm_provider and len(self.current_turn_text) > 5:
                is_complete = await self._check_semantic_completion(self.current_turn_text)
                if not is_complete:
                    logger.info(f"🤔 [SEMANTIC] Sentence incomplete: '{self.current_turn_text}'. Extending wait.")
                    # Wait additional time (giving user time to think)
                    # If they don't speak, we commit anyway.
                    await asyncio.sleep(self.semantic_timeout - self.turn_timeout)
            
            # 3. Commit Turn
            await self._commit_turn()
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Turn Monitor Error: {e}")
            # Fallback commit
            await self._commit_turn()

    async def _check_semantic_completion(self, text: str) -> bool:
        """
        Ask LLM if the sentence is complete.
        Returns True if complete, False if incomplete (likely to continue).
        """
        try:
            system_prompt = (
                "You are a helpful assistant serving as a semantic detector. "
                "Analyze the user's speech transcript. "
                "Output ONLY 'YES' if the sentence is syntactically complete and makes sense as a turn end. "
                "Output 'NO' if it seems broken, interrupted, or trailing off (e.g. 'and then...', 'because the...'). "
            )
            
            response = ""
            # Create a localized history for this check
            messages = [{"role": "user", "content": f"Text: \"{text}\""}]
            
            # Use low temperature for determinism
            async for token in self.llm_provider.get_stream(messages, system_prompt, temperature=0.0, max_tokens=5):
                response += token
                
            result = response.strip().upper()
            logger.debug(f"🔍 [SEMANTIC] Check '{text}' -> {result}")
            
            return "YES" in result
            
        except Exception as e:
            logger.warning(f"⚠️ Semantic check failed: {e}")
            return True # Fail safe: assume complete

    async def _commit_turn(self):
        text = self.current_turn_text.strip()
        if not text:
            return
            
        logger.info(f"✅ [TURN COMPLETE] User: {text}")
        
        # 1. Update History
        self.conversation_history.append({"role": "user", "content": text})
        
        # 1.1 Apply Context Window limit (NEW)
        context_window = getattr(self.config, 'context_window', 10)
        if len(self.conversation_history) > context_window:
            self.conversation_history = self.conversation_history[-context_window:]
            logger.debug(f"🧠 [CONTEXT] Truncated history to last {context_window} messages")
        
        # 2. Reset State
        self.current_turn_text = ""
        
        # 3. Trigger LLM
        await self.push_frame(TextFrame(text=text, is_final=True))
