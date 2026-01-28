import logging
import uuid
import asyncio
from typing import Any, Optional

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, SystemFrame, CancelFrame
# Import ErrorFrame if we had it, using implicit Frame for now
from app.services.base import LLMProvider
from app.core.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

class LLMProcessor(FrameProcessor):
    """
    Consumes TextFrames (User Transcripts), sends to LLM, produces TextFrames (Assistant Response).
    Supports cancellation via CancelFrame.
    """
    def __init__(self, provider: LLMProvider, config: Any, conversation_history: list, context: dict = None):
        super().__init__(name="LLMProcessor")
        self.provider = provider
        self.config = config
        self.context = context or {} # Campaign context
        self.conversation_history = conversation_history # Shared history reference (mutable)
        self.system_prompt = getattr(config, 'system_prompt', '')
        self._current_task: Optional[asyncio.Task] = None

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, TextFrame) and frame.is_final:
                # Cancel previous generation if new input arrives (implicit interruption)
                if self._current_task and not self._current_task.done():
                    self._current_task.cancel()
                
                # Start new generation task
                self._current_task = asyncio.create_task(self._handle_user_text(frame.text))
            
            elif isinstance(frame, CancelFrame):
                logger.info("🛑 [LLM] Received CancelFrame. Stopping generation.")
                if self._current_task and not self._current_task.done():
                    self._current_task.cancel()
                await self.push_frame(frame, direction)
                
            else:
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _handle_user_text(self, text: str):
        """
        Main LLM Loop:
        1. Append User msg to history.
        2. Call LLM Provider (Stream).
        3. Push TextFrame chunks or sentences downstream (to TTS).
        """
        logger.info(f"🤖 [LLM] Processing: {text}")
        
        # 1. Update History
        # Note: If ContextAggregator is upstream, it might have already added this.
        # Check if last message is this text to avoid duplication.
        if not self.conversation_history or self.conversation_history[-1].get("content") != text:
             self.conversation_history.append({"role": "user", "content": text})
        
        # 2. Add System Prompt
        system_content = self._build_system_prompt()
        
        try:
            # 3. Stream Generation
            # We need to buffer text to form sentences for TTS
            full_response_buffer = ""
            sentence_buffer = ""
            
            async for token in self.provider.get_stream(
                messages=self.conversation_history, # Only conversation history (User msg already added)
                system_prompt=system_content,
                temperature=getattr(self.config, 'temperature', 0.7),
                max_tokens=getattr(self.config, 'max_tokens', 150) # ✅ Pass config value
            ):
                token_text = token
                full_response_buffer += token_text
                sentence_buffer += token_text
                
                # Check for Special Actions (Hangup, Transfer)
                if "[END_CALL]" in token_text:
                     # TODO: Emit ControlFrame(EndCall)
                     continue
                
                # Robust Sentence Split (Simple Heuristic for now, but cleaner)
                # Check for puntuation at the end of buffer (not just 'any' inside)
                if len(sentence_buffer) > 10 and sentence_buffer.strip()[-1] in [".", "?", "!"]:
                    # Emit TextFrame for TTS
                    await self.push_frame(TextFrame(text=sentence_buffer))
                    sentence_buffer = ""
            
            # Flush remaining text to TTS
            if sentence_buffer.strip():
                 await self.push_frame(TextFrame(text=sentence_buffer))
            
            # CRITICAL FIX: Append COMPLETE response to history ONCE at the end.
            # Previous code appended fragments, corrupting context for next turn.
            if full_response_buffer.strip():
                self.conversation_history.append({"role": "assistant", "content": full_response_buffer})
                logger.debug(f"🤖 [LLM] Full Response added to history ({len(full_response_buffer)} chars)")

        except asyncio.CancelledError:
            logger.info("🛑 [LLM] Generation cancelled.")
            # Important: Do NOT swallow the CancelledError if we want others to know, 
            # but usually the task is just cancelled and we stop.
            pass
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            # await self.push_frame(ErrorFrame(error=str(e)))

    def _build_system_prompt(self):
        return PromptBuilder.build_system_prompt(self.config, self.context)
