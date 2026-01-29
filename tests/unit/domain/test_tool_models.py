"""
Unit tests for tool models (ToolDefinition, ToolRequest, ToolResponse).

Validates domain dataclasses for tool calling infrastructure.
"""
import pytest
from app.domain.models.tool_models import ToolDefinition, ToolRequest, ToolResponse


class TestToolDefinition:
    """Test suite for ToolDefinition dataclass."""
    
    def test_tool_definition_creation(self):
        """ToolDefinition should be created with required fields."""
        tool_def = ToolDefinition(
            name="query_database",
            description="Search contact database",
            parameters={
                "query": {"type": "string", "description": "Search query"}
            },
            required=["query"]
        )
        
        assert tool_def.name == "query_database"
        assert tool_def.description == "Search contact database"
        assert "query" in tool_def.parameters
        assert tool_def.required == ["query"]
    
    def test_tool_definition_default_required(self):
        """ToolDefinition.required should default to empty list."""
        tool_def = ToolDefinition(
            name="test_tool",
            description="Test",
            parameters={}
        )
        
        assert tool_def.required == []
    
    def test_to_openai_format(self):
        """to_openai_format() should export correct structure."""
        tool_def = ToolDefinition(
            name="query_database",
            description="Search contact database",
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results"}
            },
            required=["query"]
        )
        
        openai_format = tool_def.to_openai_format()
        
        assert openai_format["name"] == "query_database"
        assert openai_format["description"] == "Search contact database"
        assert openai_format["parameters"]["type"] == "object"
        assert "query" in openai_format["parameters"]["properties"]
        assert "limit" in openai_format["parameters"]["properties"]
        assert openai_format["parameters"]["required"] == ["query"]


class TestToolRequest:
    """Test suite for ToolRequest dataclass."""
    
    def test_tool_request_creation(self):
        """ToolRequest should be created with required fields."""
        request = ToolRequest(
            tool_name="query_database",
            arguments={"query": "John Smith", "limit": 5},
            trace_id="abc-123"
        )
        
        assert request.tool_name == "query_database"
        assert request.arguments == {"query": "John Smith", "limit": 5}
        assert request.trace_id == "abc-123"
    
    def test_tool_request_defaults(self):
        """ToolRequest should have sensible defaults."""
        request = ToolRequest(
            tool_name="test_tool",
            arguments={}
        )
        
        assert request.trace_id == ""
        assert request.metadata == {}
        assert request.timeout_seconds == 10.0
    
    def test_tool_request_custom_timeout(self):
        """ToolRequest should accept custom timeout."""
        request = ToolRequest(
            tool_name="slow_tool",
            arguments={},
            timeout_seconds=30.0
        )
        
        assert request.timeout_seconds == 30.0


class TestToolResponse:
    """Test suite for ToolResponse dataclass."""
    
    def test_tool_response_success(self):
        """ToolResponse should represent successful execution."""
        response = ToolResponse(
            tool_name="query_database",
            result=[{"name": "John Smith", "phone": "+123"}],
            success=True,
            execution_time_ms=45.2,
            trace_id="abc-123"
        )
        
        assert response.tool_name == "query_database"
        assert response.success is True
        assert len(response.result) == 1
        assert response.execution_time_ms == 45.2
        assert response.trace_id == "abc-123"
        assert response.error_message == ""
    
    def test_tool_response_failure(self):
        """ToolResponse should represent failed execution."""
        response = ToolResponse(
            tool_name="query_database",
            result=None,
            success=False,
            error_message="Database timeout",
            trace_id="abc-123"
        )
        
        assert response.tool_name == "query_database"
        assert response.success is False
        assert response.result is None
        assert response.error_message == "Database timeout"
    
    def test_tool_response_defaults(self):
        """ToolResponse should have sensible defaults."""
        response = ToolResponse(
            tool_name="test_tool",
            result=None,
            success=False
        )
        
        assert response.error_message == ""
        assert response.execution_time_ms == 0.0
        assert response.trace_id == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
