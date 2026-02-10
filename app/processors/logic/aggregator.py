import asyncio
import logging
from typing import Any

from app.core.frames import (
    CancelFrame,
    Frame,
    TextFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from app.core.processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)


class ContextAggregator(FrameProcessor):
    """
    Aggregates User Transcripts into coherent Turns.
    Manages Conversation History.
    Triggers LLM only when "Turn" is complete (Smart Silence).
    """
    def __init__(self, config: Any, conversation_history: list[dict], llm_provider: Any = None, transcript_callback=None):
        super().__init__(name="ContextAggregator")
        self.config = config
        # NOTE: conversation_history is a shared mutable list reference.
        # It MUST be modified in-place to maintain sync with Orchestrator.
        self.conversation_history = conversation_history
        self.llm_provider = llm_provider
        self.transcript_callback = transcript_callback


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
                # Push downstream to pause TTS if needed (Barge-in mechanics)
                await self.push_frame(frame, direction)

            elif isinstance(frame, UserStoppedSpeakingFrame):
                await self._handle_stopped_speaking()
                # Push downstream
                await self.push_frame(frame, direction)

            elif isinstance(frame, TextFrame) or type(frame).__name__ == "TextFrame":
                # [DEBUG] Trace Greeting
                role = frame.metadata.get('role')
                src = frame.metadata.get('source')
                logger.info(f"🧐 [AGG DEBUG] TextFrame: '{getattr(frame, 'text', '')[:30]}...' | Role: {role} | Source: {src}")

                # Is it System/Assistant output? Pass through immediately.
                if role == 'assistant' or src == 'system':
                    logger.info("⏩ [AGG] Bypassing System TextFrame")
                    
                    # [FIX] Report Immediate Assistant/System messages (e.g. Greeting) to UI
                    if self.transcript_callback:
                        # Ensure we don't block
                        if asyncio.iscoroutinefunction(self.transcript_callback):
                            asyncio.create_task(self.transcript_callback("assistant", getattr(frame, 'text', '')))
                            
                    await self.push_frame(frame, direction)
                else:
                    # User Input: Aggregate turn
                    logger.debug(f"🛑 [AGG DEBUG] Processing User Text: '{getattr(frame, 'text', '')}'")
                    await self._handle_text(getattr(frame, 'text', ''))

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

        # Barge-in: Send cancel signal downstream
        await self.push_frame(CancelFrame(reason="User Barge-In"))

    async def _handle_stopped_speaking(self):
        self.user_speaking = False
        # Start Turn Timer if we have accumulated text
        if self.current_turn_text:
            self._turn_timer_task = asyncio.create_task(self._monitor_turn_completion())

    async def _handle_text(self, text: str):
        if not text.strip():
            return

        # [FEEDBACK] Immediately emit partial text for UI/Reporter
        # This frame is marked 'partial' so LLM ignores it, but Reporter sees it.
        # [FEEDBACK] Immediately emit partial text for UI/Reporter
        if self.transcript_callback:
            # Report partial transcript
            # Note: We need to ensure we don't block. 
            # If callback is async, use create_task or run_coroutine_threadsafe if needed.
            # Assuming callback is async and we are in async context:
            if asyncio.iscoroutinefunction(self.transcript_callback):
                asyncio.create_task(self.transcript_callback("user", text))

        # This frame is marked 'partial' so LLM ignores it, but Reporter sees it.
        await self.push_frame(
             TextFrame(
                 text=text, 
                 is_final=False, 
                 metadata={'turn_status': 'partial', 'role': 'user'}
             ),
             FrameDirection.DOWNSTREAM
        )

        # Append to current turn buffer
        self.current_turn_text += " " + text

        # If user is NOT speaking (e.g. short utterance where VAD stopped before Text arrived),
        # we should start the timer immediately.
        if not self.user_speaking:
             if self._turn_timer_task:
                 self._turn_timer_task.cancel()
             self._turn_timer_task = asyncio.create_task(self._monitor_turn_completion())

    async def _monitor_turn_completion(self):
        try:
            # 1. Wait initial short timeout (e.g. 0.6s)
            await asyncio.sleep(self.turn_timeout)

            # 2. Semantic Check (if enabled and provider available)
            strategy = getattr(self.config, 'segmentation_strategy', 'default')

            if strategy == 'semantic' and self.llm_provider and len(self.current_turn_text) > 5:
                is_complete = await self._check_semantic_completion(self.current_turn_text)
                if not is_complete:
                    logger.info(f"🤔 [SEMANTIC] Sentence incomplete: '{self.current_turn_text}'. Extending wait.")
                    # Wait additional time (giving user time to think)
                    await asyncio.sleep(self.semantic_timeout - self.turn_timeout)

            # 3. Commit Turn
            await self._commit_turn()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Turn Monitor Error: {e}")
            # Fallback commit on error to avoid stalling
            await self._commit_turn()

    async def _check_semantic_completion(self, text: str) -> bool:
        """
        Ask LLM if the sentence is complete.
        Returns True if complete, False if incomplete.
        """
        try:
            system_prompt = (
                "You are a helpful assistant serving as a semantic detector. "
                "Analyze the user's speech transcript. "
                "Output ONLY 'YES' if the sentence is syntactically complete and makes sense as a turn end. "
                "Output 'NO' if it seems broken, interrupted, or trailing off."
            )

            response = ""
            messages = [{"role": "user", "content": f"Text: \"{text}\""}]

            # Use low temperature for determinism
            async for token in self.llm_provider.get_stream(messages, system_prompt, temperature=0.0, max_tokens=5):
                response += token

            result = response.strip().upper()
            return "YES" in result

        except Exception as e:
            # Fail safe: assume complete to proceed
            logger.warning(f"⚠️ Semantic check failed: {e}")
            return True

    async def _commit_turn(self):
        text = self.current_turn_text.strip()
        if not text:
            return

        logger.info(f"✅ [TURN COMPLETE] User: {text}")

        # 1. Update SHARED History (In-Place Mutation)
        self.conversation_history.append({"role": "user", "content": text})

        # 1.1 Apply Context Window limit
        context_window = getattr(self.config, 'context_window', 10)
        if len(self.conversation_history) > context_window:
            # OPTIMIZATION: Delete from head instead of reassigning variable
            # This preserves the list reference for other observers (e.g. Orchestrator)
            excess = len(self.conversation_history) - context_window
            del self.conversation_history[:excess]
            logger.debug(f"🧠 [CONTEXT] Truncated history to last {context_window} messages")

        # 2. Reset State
        self.current_turn_text = ""

        # 3. Trigger LLM by pushing Final TextFrame
        # Marked 'complete' so LLM knows to process it.
        await self.push_frame(
            TextFrame(
                text=text, 
                is_final=True,
                metadata={'turn_status': 'complete', 'role': 'user'}
            )
        )
