import logging
import uuid
import asyncio
from typing import Any, Optional

from app.core.processor import FrameProcessor, FrameDirection
from app.core.frames import Frame, TextFrame, SystemFrame, CancelFrame
from app.domain.ports import LLMPort, LLMRequest, LLMMessage  # ✅ Module 9: Use LLMPort
from app.core.prompt_builder import PromptBuilder
from app.domain.models.llm_models import LLMChunk, LLMFunctionCall  # ✅ Module 9
from app.domain.models.tool_models import ToolRequest  # ✅ Module 9
from app.domain.use_cases import ExecuteToolUseCase  # ✅ Module 9
from app.core.audio.hold_audio import HoldAudioPlayer  # ✅ Module 10

logger = logging.getLogger(__name__)

class LLMProcessor(FrameProcessor):
    """
    Consumes TextFrames (User Transcripts), sends to LLM via LLMPort, produces TextFrames (Assistant Response).
    
    ✅ Module 9: Refactored to use LLMPort (hexagonal)
    ✅ Module 9: Supports function calling (tool execution)
    ✅ Module 9: Processes LLMChunk (text + function_call)
    ✅ Module 10: Hold audio during tool execution (UX improvement)
    """
    def __init__(
        self, 
        llm_port: LLMPort,  # ✅ Use LLMPort instead of LLMProvider
        config: Any, 
        conversation_history: list, 
        context: dict = None,
        execute_tool_use_case: Optional[ExecuteToolUseCase] = None,  # ✅ Module 9
        trace_id: str = None,  # ✅ Module 3
        hold_audio_player: Optional[HoldAudioPlayer] = None  # ✅ Module 10
    ):
        super().__init__(name="LLMProcessor")
        self.llm_port = llm_port
        self.config = config
        self.context = context or {}  # Campaign context
        self.conversation_history = conversation_history  # Shared history reference (mutable)
        self.system_prompt = getattr(config, 'system_prompt', '')
        self.execute_tool = execute_tool_use_case  # ✅ Module 9
        self.trace_id = trace_id or str(uuid.uuid4())  # ✅ Module 3
        self.hold_audio_player = hold_audio_player  # ✅ Module 10
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
        Main LLM Loop (✅ Module 9: Refactored for function calling):
        1. Append User msg to history.
        2. Call LLM via LLMPort (streaming with tools support).
        3. Process LLMChunks:
           - Text → Push to TTS
           - Function call → Execute tool → Re-call LLM with result
        """
        logger.info(f"🤖 [LLM] trace={self.trace_id} Processing: {text[:50]}...")
        
        # 1. Update History
        if not self.conversation_history or self.conversation_history[-1].get("content") != text:
            self.conversation_history.append({"role": "user", "content": text})
        
        try:
            await self._generate_llm_response()
        
        except asyncio.CancelledError:
            logger.info(f"🛑 [LLM] trace={self.trace_id} Generation cancelled.")
            pass
        except Exception as e:
            logger.error(f"[LLM] trace={self.trace_id} Error: {e}")

    async def _generate_llm_response(self, tool_result_message: dict = None):
        """
        Generate LLM response (supports function calling loop).
        
        Args:
            tool_result_message: Optional tool result message for function calling continuation
        """
        # Apply Context Window Logic
        context_window = getattr(self.config, 'context_window', 10)
        
        # Slice history if window is set (and valid positive integer)
        if isinstance(context_window, int) and context_window > 0:
            history_slice = self.conversation_history[-context_window:]
            logger.debug(f"[LLM] Context window applied: {len(history_slice)}/{len(self.conversation_history)} messages")
        else:
            history_slice = self.conversation_history

        # Build messages for LLM
        messages = [LLMMessage(role=msg["role"], content=msg["content"]) 
                    for msg in history_slice]
        
        # Add tool result if provided (function calling continuation)
        if tool_result_message:
            messages.append(LLMMessage(
                role=tool_result_message["role"], 
                content=tool_result_message["content"]
            ))
        
        # ✅ Module 9: Prepare tools for function calling
        tools = None
        if self.execute_tool and self.execute_tool.tool_count > 0:
            tools = [
                tool_def.to_openai_format() 
                for tool_def in self.execute_tool.get_tool_definitions()
            ]
        
        # Build LLM request
        request = LLMRequest(
            messages=messages,
            model=getattr(self.config, 'llm_model', 'llama-3.3-70b-versatile'),
            temperature=getattr(self.config, 'temperature', 0.7),
            max_tokens=getattr(self.config, 'max_tokens', 600),
            system_prompt=self._build_system_prompt(),
            tools=tools,  # ✅ Module 9: Function calling
            metadata={"trace_id": self.trace_id}  # ✅ Module 3
        )
        
        # Stream generation
        full_response_buffer = ""
        sentence_buffer = ""
        
        async for chunk in self.llm_port.generate_stream(request):
            # ✅ Module 9: Handle function call
            if chunk.has_function_call:
                logger.info(
                    f"🔧 [LLM] trace={self.trace_id} Function call: "
                    f"{chunk.function_call.name}({list(chunk.function_call.arguments.keys())})"
                )
                
                # Execute tool
                tool_response = await self._execute_tool(chunk.function_call)
                
                # Add assistant's function call to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"[TOOL_CALL: {chunk.function_call.name}]"
                })
                
                # Add tool result to history
                tool_result_content = (
                    f"Tool '{tool_response.tool_name}' returned: {tool_response.result}"
                    if tool_response.success
                    else f"Tool '{tool_response.tool_name}' failed: {tool_response.error_message}"
                )
                
                # ✅ Re-call LLM with tool result (function calling loop)
                await self._generate_llm_response(
                    tool_result_message={
                        "role": "function",
                        "content": tool_result_content
                    }
                )
                
                # Return to avoid duplicate history append
                return
            
            # ✅ Handle text content (normal response)
            elif chunk.has_text:
                token_text = chunk.text
                full_response_buffer += token_text
                sentence_buffer += token_text
                
                # Check for Special Actions
                if "[END_CALL]" in token_text:
                    continue
                
                # Sentence split heuristic
                if len(sentence_buffer) > 10 and sentence_buffer.strip()[-1] in [".", "?", "!"]:
                    # Emit TextFrame for TTS
                    await self.push_frame(TextFrame(text=sentence_buffer))
                    sentence_buffer = ""
        
        # Flush remaining text to TTS
        if sentence_buffer.strip():
            await self.push_frame(TextFrame(text=sentence_buffer))
        
        # Append complete response to history
        if full_response_buffer.strip():
            self.conversation_history.append({
                "role": "assistant", 
                "content": full_response_buffer
            })
            logger.debug(
                f"🤖 [LLM] trace={self.trace_id} Response added to history "
                f"({len(full_response_buffer)} chars)"
            )

    async def _execute_tool(self, function_call: LLMFunctionCall):
        """
        Execute tool via ExecuteToolUseCase.
        
        ✅ Module 10: Play hold audio during execution (UX improvement)
        
        Args:
            function_call: Function call from LLM
        
        Returns:
            ToolResponse
        """
        if not self.execute_tool:
            logger.error(f"[LLM] trace={self.trace_id} No ExecuteToolUseCase configured")
            from app.domain.models.tool_models import ToolResponse
            return ToolResponse(
                tool_name=function_call.name,
                result=None,
                success=False,
                error_message="Tool execution not configured"
            )
        
        tool_request = ToolRequest(
            tool_name=function_call.name,
            arguments=function_call.arguments,
            trace_id=self.trace_id
        )
        
        logger.info(
            f"🔧 [LLM] trace={self.trace_id} Executing tool: "
            f"{tool_request.tool_name}({tool_request.arguments})"
        )
        
        # ✅ Module 10: Start hold audio (prevent silence during tool execution)
        if self.hold_audio_player:
            await self.hold_audio_player.start()
        
        try:
            # Execute tool (async, may take 2-5s for DB queries)
            tool_response = await self.execute_tool.execute(tool_request)
        finally:
            # ✅ Module 10: Stop hold audio (tool execution complete)
            if self.hold_audio_player:
                await self.hold_audio_player.stop()
        
        logger.info(
            f"🔧 [LLM] trace={self.trace_id} Tool result: "
            f"success={tool_response.success} "
            f"result={str(tool_response.result)[:100]}"
        )
        
        return tool_response

    def _build_system_prompt(self):
        return PromptBuilder.build_system_prompt(self.config, self.context)
