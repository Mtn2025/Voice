"""
Unit tests for ExecuteToolUseCase.

Validates domain use case for tool orchestration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.use_cases.execute_tool import ExecuteToolUseCase
from app.domain.models.tool_models import ToolRequest, ToolResponse, ToolDefinition
from app.domain.ports.tool_port import ToolPort


class MockTool(ToolPort):
    """Mock tool for testing."""
    
    def __init__(self, name: str, should_succeed: bool = True):
        self._name = name
        self._should_succeed = should_succeed
    
    @property
    def name(self) -> str:
        return self._name
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description=f"Mock tool {self._name}",
            parameters={"test": {"type": "string"}},
            required=[]
        )
    
    async def execute(self, request: ToolRequest) -> ToolResponse:
        if self._should_succeed:
            return ToolResponse(
                tool_name=self._name,
                result={"mock": "data"},
                success=True,
                execution_time_ms=10.0,
                trace_id=request.trace_id
            )
        else:
            return ToolResponse(
                tool_name=self._name,
                result=None,
                success=False,
                error_message="Mock tool failed",
                trace_id=request.trace_id
            )


class TestExecuteToolUseCase:
    """Test suite for ExecuteToolUseCase."""
    
    def test_initialization(self):
        """Use case should initialize with tools dictionary."""
        tool1 = MockTool("tool_1")
        tool2 = MockTool("tool_2")
        tools = {tool1.name: tool1, tool2.name: tool2}
        
        use_case = ExecuteToolUseCase(tools)
        
        assert use_case.tool_count == 2
        assert use_case.has_tool("tool_1")
        assert use_case.has_tool("tool_2")
        assert not use_case.has_tool("nonexistent")
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """execute() should call tool and return successful response."""
        tool = MockTool("test_tool", should_succeed=True)
        use_case = ExecuteToolUseCase({tool.name: tool})
        
        request = ToolRequest(
            tool_name="test_tool",
            arguments={"test": "value"},
            trace_id="abc-123"
        )
        
        response = await use_case.execute(request)
        
        assert response.success is True
        assert response.tool_name == "test_tool"
        assert response.result == {"mock": "data"}
        assert response.trace_id == "abc-123"
    
    @pytest.mark.asyncio
    async def test_execute_tool_failure(self):
        """execute() should return error response if tool fails."""
        tool = MockTool("test_tool", should_succeed=False)
        use_case = ExecuteToolUseCase({tool.name: tool})
        
        request = ToolRequest(
            tool_name="test_tool",
            arguments={},
            trace_id="abc-123"
        )
        
        response = await use_case.execute(request)
        
        assert response.success is False
        assert response.tool_name == "test_tool"
        assert response.result is None
        assert "Mock tool failed" in response.error_message
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """execute() should return error if tool doesn't exist."""
        use_case = ExecuteToolUseCase({})
        
        request = ToolRequest(
            tool_name="nonexistent_tool",
            arguments={},
            trace_id="abc-123"
        )
        
        response = await use_case.execute(request)
        
        assert response.success is False
        assert response.tool_name == "nonexistent_tool"
        assert "not found" in response.error_message.lower()
    
    def test_get_tool_definitions(self):
        """get_tool_definitions() should return all tool schemas."""
        tool1 = MockTool("tool_1")
        tool2 = MockTool("tool_2")
        use_case = ExecuteToolUseCase({
            tool1.name: tool1,
            tool2.name: tool2
        })
        
        definitions = use_case.get_tool_definitions()
        
        assert len(definitions) == 2
        assert all(isinstance(d, ToolDefinition) for d in definitions)
        assert definitions[0].name in ["tool_1", "tool_2"]
        assert definitions[1].name in ["tool_1", "tool_2"]
    
    def test_has_tool(self):
        """has_tool() should check tool existence."""
        tool = MockTool("test_tool")
        use_case = ExecuteToolUseCase({tool.name: tool})
        
        assert use_case.has_tool("test_tool") is True
        assert use_case.has_tool("nonexistent") is False
    
    def test_tool_count(self):
        """tool_count should return number of registered tools."""
        tools = {
            MockTool("tool_1").name: MockTool("tool_1"),
            MockTool("tool_2").name: MockTool("tool_2"),
            MockTool("tool_3").name: MockTool("tool_3")
        }
        use_case = ExecuteToolUseCase(tools)
        
        assert use_case.tool_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
