import logging
import uuid
import asyncio
from typing import Any, Optional

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, SystemFrame, CancelFrame
# Import ErrorFrame if we had it, using implicit Frame for now
from app.services.base import LLMProvider

logger = logging.getLogger(__name__)

class LLMProcessor(FrameProcessor):
    """
    Consumes TextFrames (User Transcripts), sends to LLM, produces TextFrames (Assistant Response).
    Supports cancellation via CancelFrame.
    """
    def __init__(self, provider: LLMProvider, config: Any, conversation_history: list):
        super().__init__(name="LLMProcessor")
        self.provider = provider
        self.config = config
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
        
        # 2. Add System Prompt (if not handled by provider internal context)
        # In Andrea, orchestrator builds system prompt. 
        # We assume provider.generate_response handles the context or we pass it.
        # Looking at Orchestrator, it calls `self.llm_provider.generate_response(transcript, ...)`
        # Actually it calls `generate_response_stream` or similar.
        # Let's assume standard Andrea provider interface: `generate_stream(messages, ...)`
        
        messages = [{"role": "system", "content": self._build_system_prompt()}] + self.conversation_history
        
        try:
            # 3. Stream Generation
            # We need to buffer text to form sentences for TTS
            sentence_buffer = ""
            
            async for token in self.provider.generate_stream(messages):
                # Check for control tokens
                token_text = token
                
                # Check for Special Actions (Hangup, Transfer) - Logic from Orchestrator
                # Simplified here for brevity, should port full logic
                if "[END_CALL]" in token_text:
                    # Emit Hangup System Frame?
                    # await self.push_frame(EndFrame(reason="LLM Request"))
                    continue
                
                sentence_buffer += token_text
                
                # Simple sentence split (Naive) - Better to use a tokenizer or the orchestrated split logic
                if any(punct in sentence_buffer for punct in [".", "?", "!"]):
                    # Emit TextFrame
                    await self.push_frame(TextFrame(text=sentence_buffer))
                    # Add to history
                    self.conversation_history.append({"role": "assistant", "content": sentence_buffer})
                    sentence_buffer = ""
            
            # Flush remaining
            if sentence_buffer:
                 await self.push_frame(TextFrame(text=sentence_buffer))
                 self.conversation_history.append({"role": "assistant", "content": sentence_buffer})

        except asyncio.CancelledError:
            logger.info("🛑 [LLM] Generation cancelled.")
            # Important: Do NOT swallow the CancelledError if we want others to know, 
            # but usually the task is just cancelled and we stop.
            pass
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            # await self.push_frame(ErrorFrame(error=str(e)))

    def _build_system_prompt(self):
        # reuse orchestrator logic or simplified version
        return self.system_prompt
