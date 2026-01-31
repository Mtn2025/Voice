import asyncio
import logging
import re
import uuid
from typing import Any

from app.core.audio.hold_audio import HoldAudioPlayer
from app.core.frames import CancelFrame, EndTaskFrame, Frame, TextFrame
from app.core.processor import FrameDirection, FrameProcessor
from app.core.prompt_builder import PromptBuilder
from app.domain.models.llm_models import LLMFunctionCall
from app.domain.models.tool_models import ToolRequest
from app.domain.ports import LLMMessage, LLMPort, LLMRequest
from app.domain.use_cases import ExecuteToolUseCase

logger = logging.getLogger(__name__)

class LLMProcessor(FrameProcessor):
    """
    Consumes TextFrames (User Transcripts), sends to LLM via LLMPort, produces TextFrames (Assistant Response).
    Handles function calling, hold audio, and conversation history.
    """
    def __init__(
        self,
        llm_port: LLMPort,
        config: Any,
        conversation_history: list,
        context: dict | None = None,
        execute_tool_use_case: ExecuteToolUseCase | None = None,
        trace_id: str | None = None,
        hold_audio_player: HoldAudioPlayer | None = None
    ):
        super().__init__(name="LLMProcessor")
        self.llm_port = llm_port
        self.config = config
        self.context = context or {}
        self.conversation_history = conversation_history
        self.system_prompt = getattr(config, 'system_prompt', '')
        self.execute_tool = execute_tool_use_case
        self.trace_id = trace_id or str(uuid.uuid4())
        self.hold_audio_player = hold_audio_player
        self._current_task: asyncio.Task | None = None

    async def process_frame(self, frame: Frame, direction: int):
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, TextFrame) and frame.is_final:
                # Implicit interruption: cancel previous generation
                if self._current_task and not self._current_task.done():
                    self._current_task.cancel()

                # Start new generation
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
        1. Update history.
        2. Generate response (streaming).
        3. Handle Function Calls.
        """
        logger.info(f"🤖 [LLM] trace={self.trace_id} Processing: {text[:50]}...")

        # 1. Update History (Deduplicated logic)
        if not self.conversation_history or self.conversation_history[-1].get("content") != text:
            self.conversation_history.append({"role": "user", "content": text})

        try:
            await self._generate_llm_response()

        except asyncio.CancelledError:
            logger.info(f"🛑 [LLM] trace={self.trace_id} Generation cancelled.")
            pass
        except Exception as e:
            logger.error(f"[LLM] trace={self.trace_id} Error: {e}", exc_info=True)

    async def _generate_llm_response(self, tool_result_message: dict | None = None):
        """
        Generate LLM response suitable for conversation loop.
        """
        # Apply Logic: Context Window
        context_window = getattr(self.config, 'context_window', 10)

        if isinstance(context_window, int) and context_window > 0:
            history_slice = self.conversation_history[-context_window:]
        else:
            history_slice = self.conversation_history

        # Build messages
        messages = [LLMMessage(role=msg["role"], content=msg["content"])
                    for msg in history_slice]

        # Continuation (Function Calling)
        if tool_result_message:
            messages.append(LLMMessage(
                role=tool_result_message["role"],
                content=tool_result_message["content"]
            ))

        # Prepare Tools
        tools = None
        if self.execute_tool and self.execute_tool.tool_count > 0:
            tools = [
                tool_def.to_openai_format()
                for tool_def in self.execute_tool.get_tool_definitions()
            ]

        # Request
        request = LLMRequest(
            messages=messages,
            model=getattr(self.config, 'llm_model', 'llama-3.3-70b-versatile'),
            temperature=getattr(self.config, 'temperature', 0.7),
            max_tokens=getattr(self.config, 'max_tokens', 600),
            system_prompt=self._build_system_prompt(),
            tools=tools,
            metadata={"trace_id": self.trace_id},
            frequency_penalty=getattr(self.config, 'frequency_penalty', 0.0),
            presence_penalty=getattr(self.config, 'presence_penalty', 0.0)
        )

        # Stream
        full_response_buffer = ""
        sentence_buffer = ""
        should_end_call = False

        async for chunk in self.llm_port.generate_stream(request):
            # Case A: Function Call
            if chunk.has_function_call:
                logger.info(
                    f"🔧 [LLM] trace={self.trace_id} Function call: "
                    f"{chunk.function_call.name}({list(chunk.function_call.arguments.keys())})"
                )

                tool_response = await self._execute_tool(chunk.function_call)

                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"[TOOL_CALL: {chunk.function_call.name}]"
                })

                tool_result_content = (
                    f"Tool '{tool_response.tool_name}' returned: {tool_response.result}"
                    if tool_response.success
                    else f"Tool '{tool_response.tool_name}' failed: {tool_response.error_message}"
                )

                # Recursive Loop
                await self._generate_llm_response(
                    tool_result_message={
                        "role": "function",
                        "content": tool_result_content
                    }
                )
                return

            # Case B: Text Content
            if chunk.has_text:
                token_text = chunk.text
                full_response_buffer += token_text

                # Check for [END_CALL] tag
                if "[END_CALL]" in token_text:
                    should_end_call = True
                    token_text = token_text.replace("[END_CALL]", "") # Remove from speech

                sentence_buffer += token_text

                # Smart heuristic for sentence splitting (Punctuation + Space or End of Line)
                # Adds logical pause for TTS
                if len(sentence_buffer) > 10 and re.search(r'[.?!]\s+$', sentence_buffer):
                    await self.push_frame(TextFrame(text=sentence_buffer, trace_id=self.trace_id))
                    sentence_buffer = ""

        # Flush remaining text
        if sentence_buffer.strip():
            await self.push_frame(TextFrame(text=sentence_buffer, trace_id=self.trace_id))

        # Update History
        if full_response_buffer.strip():
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response_buffer
            })

        # Handle End Call Signal
        if should_end_call:
            logger.info("📞 [LLM] Detected [END_CALL] signal. Initiating hangup.")
            # Send SystemFrame to trigger architecture shutdown flow
            await self.push_frame(EndTaskFrame(), FrameDirection.DOWNSTREAM)

    async def _execute_tool(self, function_call: LLMFunctionCall):
        """
        Execute tool via ExecuteToolUseCase.
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

        # Dynamic Config
        tool_url = getattr(self.config, 'tool_server_url', None)
        tool_secret = getattr(self.config, 'tool_server_secret', None)
        tool_timeout = getattr(self.config, 'tool_timeout_ms', 5000) / 1000.0

        tool_request = ToolRequest(
            tool_name=function_call.name,
            arguments=function_call.arguments,
            trace_id=self.trace_id,
            timeout_seconds=tool_timeout,
            context={
                "server_url": tool_url,
                "server_secret": tool_secret
            }
        )

        logger.info(f"🔧 [LLM] Executing tool: {tool_request.tool_name}")

        # Hold Audio UX
        if self.hold_audio_player:
            await self.hold_audio_player.start()

        try:
            tool_response = await self.execute_tool.execute(tool_request)
        finally:
            if self.hold_audio_player:
                await self.hold_audio_player.stop()

        logger.info(f"🔧 [LLM] Tool result success={tool_response.success}")
        return tool_response

    def _build_system_prompt(self):
        return PromptBuilder.build_system_prompt(self.config, self.context)
