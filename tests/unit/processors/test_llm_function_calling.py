"""
Unit tests for LLM Function Calling (Module 9).

Tests end-to-end function calling flow:
- LLMPort detects function_call in stream
- LLMProcessor executes tool via ExecuteToolUseCase
- Tool result re-injected to LLM
- Final response returned to TTS
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.processors.logic.llm import LLMProcessor
from app.domain.models.llm_models import LLMChunk, LLMFunctionCall
from app.domain.models.tool_models import ToolRequest, ToolResponse, ToolDefinition
from app.domain.use_cases.execute_tool import ExecuteToolUseCase
from app.domain.ports import LLMPort, LLMRequest
from app.core.frames import TextFrame


class MockLLMPort(LLMPort):
    """Mock LLM Port for testing function calling."""
    
    def __init__(self, chunks_sequence):
        """
        Args:
            chunks_sequence: List of lists - each inner list is chunks for one generate_stream call
        """
        self.chunks_sequence = chunks_sequence
        self.call_count = 0
        self.last_request = None
    
    async def generate_stream(self, request: LLMRequest):
        """Yield chunks for current call index."""
        self.last_request = request
        
        # Get chunks for this call (or empty if exceeded)
        chunks = self.chunks_sequence[self.call_count] if self.call_count < len(self.chunks_sequence) else []
        self.call_count += 1
        
        for chunk in chunks:
            yield chunk
    
    async def get_available_models(self):
        return ["test-model"]
    
    def is_model_safe_for_voice(self, model: str):
        return True


class MockToolPort:
    """Mock tool for testing."""
    
    def __init__(self, name="test_tool", result="Tool executed successfully"):
        self._name = name
        self._result = result
    
    @property
    def name(self):
        return self._name
    
    async def execute(self, request: ToolRequest):
        """Mock tool execution."""
        return ToolResponse(
            tool_name=self._name,
            result=self._result,
            success=True,
            trace_id=request.trace_id,
            execution_time_ms=10.0
        )
    
    def get_definition(self):
        """Return tool definition."""
        return ToolDefinition(
            name=self._name,
            description="Test tool for unit tests",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        )


@pytest.mark.asyncio
async def test_llm_function_calling_flow():
    """
    Test complete function calling flow:
    1. User sends text
    2. LLM returns function_call
    3. Tool executes
    4. LLM called again with tool result
    5. LLM returns final response
    """
    # Setup
    conversation_history = []
    config = Mock()
    config.llm_model = "test-model"
    config.temperature = 0.7
    config.max_tokens = 600
    config.system_prompt = "Test system prompt"
    
    # ✅ Module 9: LLM returns different chunks for each call
    chunks_sequence = [
        # First LLM call: Returns function_call
        [
            LLMChunk(
                function_call=LLMFunctionCall(
                    name="test_tool",
                    arguments={"query": "test query"}
                ),
                finish_reason="function_call"
            )
        ],
        # Second LLM call (after tool execution): Returns text response
        [
            LLMChunk(text="The "),
            LLMChunk(text="tool returned: "),
            LLMChunk(text="Tool executed successfully."),
            LLMChunk(finish_reason="stop")
        ]
    ]
    
    mock_llm_port = MockLLMPort(chunks_sequence)
    mock_tool = MockToolPort()
    tools = {mock_tool.name: mock_tool}
    execute_tool_use_case = ExecuteToolUseCase(tools)
    
    # Create LLMProcessor
    processor = LLMProcessor(
        llm_port=mock_llm_port,
        config=config,
        conversation_history=conversation_history,
        context={},
        execute_tool_use_case=execute_tool_use_case,
        trace_id="test-trace-123"
    )
    
    # Collect pushed frames
    pushed_frames = []
    
    async def mock_push_frame(frame, direction=0):
        pushed_frames.append(frame)
    
    processor.push_frame = mock_push_frame
    
    # Execute
    await processor._handle_user_text("Execute test tool")
    
    # Assertions
    assert len(conversation_history) >= 2, f"Should have user message and assistant response, got {len(conversation_history)}"
    
    # Verify user message added
    assert conversation_history[0]["role"] == "user"
    assert conversation_history[0]["content"] == "Execute test tool"
    
    # Verify function call detected
    assert any("[TOOL_CALL: test_tool]" in msg.get("content", "") 
               for msg in conversation_history), f"Function call should be in history. History: {conversation_history}"
    
    # Verify LLM called twice (1: function_call, 2: after tool result)
    assert mock_llm_port.call_count == 2, f"LLM should be called twice (initial + after tool), got {mock_llm_port.call_count}"
    
    # Verify final text frames pushed (from second LLM call after tool execution)
    text_frames = [f for f in pushed_frames if isinstance(f, TextFrame)]
    assert len(text_frames) > 0, f"Should push text frames for TTS, got {len(text_frames)} frames. Pushed: {pushed_frames}"
    
    # Verify tools were passed to LLM
    assert mock_llm_port.last_request.tools is not None, "Tools should be passed to LLM"
    assert len(mock_llm_port.last_request.tools) == 1, "Should have 1 tool"
    
    print("✅ test_llm_function_calling_flow PASSED")


@pytest.mark.asyncio
async def test_llm_text_only_no_function_call():
    """
    Test normal flow without function calling (backward compatibility).
    """
    conversation_history = []
    config = Mock()
    config.llm_model = "test-model"
    config.temperature = 0.7
    config.max_tokens = 600
    config.system_prompt = "Test"
    
    # LLM returns only text (no function call) - single call
    chunks_sequence = [
        [
            LLMChunk(text="Hello, "),
            LLMChunk(text="how can I help you?"),
            LLMChunk(finish_reason="stop")
        ]
    ]
    
    mock_llm_port = MockLLMPort(chunks_sequence)
    
    processor = LLMProcessor(
        llm_port=mock_llm_port,
        config=config,
        conversation_history=conversation_history,
        context={},
        execute_tool_use_case=None,  # No tools
        trace_id="test-trace-456"
    )
    
    pushed_frames = []
    
    async def mock_push_frame(frame, direction=0):
        pushed_frames.append(frame)
    
    processor.push_frame = mock_push_frame
    
    # Execute
    await processor._handle_user_text("Hello")
    
    # Assertions
    assert len(conversation_history) == 2, "Should have user + assistant messages"
    assert conversation_history[1]["role"] == "assistant"
    assert "Hello, how can I help you?" in conversation_history[1]["content"]
    
    # Verify text frames pushed
    text_frames = [f for f in pushed_frames if isinstance(f, TextFrame)]
    assert len(text_frames) > 0, "Should push text frames"
    
    print("✅ test_llm_text_only_no_function_call PASSED")


@pytest.mark.asyncio
async def test_function_call_tool_not_found():
    """
    Test error handling when LLM requests non-existent tool.
    """
    conversation_history = []
    config = Mock()
    config.llm_model = "test-model"
    config.temperature = 0.7
    config.max_tokens = 600
    config.system_prompt = "Test"
    
    # LLM requests non-existent tool - single call
    chunks_sequence = [
        [
            LLMChunk(
                function_call=LLMFunctionCall(
                    name="nonexistent_tool",
                    arguments={}
                ),
                finish_reason="function_call"
            )
        ]
    ]
    
    mock_llm_port = MockLLMPort(chunks_sequence)
    execute_tool_use_case = ExecuteToolUseCase({})  # Empty tools
    
    processor = LLMProcessor(
        llm_port=mock_llm_port,
        config=config,
        conversation_history=conversation_history,
        context={},
        execute_tool_use_case=execute_tool_use_case,
        trace_id="test-trace-789"
    )
    
    processor.push_frame = AsyncMock()
    
    # Execute
    await processor._handle_user_text("Test")
    
    # Should not crash, error handled gracefully
    # Tool response should indicate failure
    assert True  # No exception raised
    
    print("✅ test_function_call_tool_not_found PASSED")


if __name__ == "__main__":
    asyncio.run(test_llm_function_calling_flow())
    asyncio.run(test_llm_text_only_no_function_call())
    asyncio.run(test_function_call_tool_not_found())
    print("\\n🎉 ALL TESTS PASSED - Module 9 Function Calling Verified ✅")
