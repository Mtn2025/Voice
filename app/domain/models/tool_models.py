"""
Tool models for LLM function calling.

Domain models defining tool communication contracts (Hexagonal Architecture).
Compatible with OpenAI function calling format.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    """
    Tool metadata exportable for LLM function calling.

    Compatible with OpenAI/Groq function calling format.

    Example:
        >>> tool_def = ToolDefinition(
        ...     name="query_database",
        ...     description="Search contact database",
        ...     parameters={
        ...         "query": {"type": "string", "description": "Search query"},
        ...         "limit": {"type": "integer", "description": "Max results", "default": 5}
        ...     },
        ...     required=["query"]
        ... )
        >>> tool_def.to_openai_format()
        {
            "name": "query_database",
            "description": "Search contact database",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": ["query"]
            }
        }
    """
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema properties
    required: list[str] = field(default_factory=list)

    def to_openai_format(self) -> dict[str, Any]:
        """
        Export to OpenAI/Groq function calling format.

        Returns:
            Dictionary compatible with OpenAI functions API
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
        }


@dataclass
class ToolRequest:
    """
    Request to execute a tool.

    Contains tool name, arguments, and execution context (trace_id, timeout).

    Example:
        >>> request = ToolRequest(
        ...     tool_name="query_database",
        ...     arguments={"query": "John Smith", "limit": 5},
        ...     trace_id="abc-123",
        ...     timeout_seconds=10.0
        ... )
    """
    tool_name: str
    arguments: dict[str, Any]
    trace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 10.0  # Default 10s timeout
    context: dict[str, Any] = field(default_factory=dict)  # Phase VI: Dynamic Config (URL, Secret)


@dataclass
class ToolResponse:
    """
    Response from tool execution.

    Contains result (if successful), error message (if failed), and metrics.

    Example (success):
        >>> response = ToolResponse(
        ...     tool_name="query_database",
        ...     result=[{"name": "John Smith", "phone": "+123"}],
        ...     success=True,
        ...     execution_time_ms=45.2,
        ...     trace_id="abc-123"
        ... )

    Example (failure):
        >>> response = ToolResponse(
        ...     tool_name="query_database",
        ...     result=None,
        ...     success=False,
        ...     error_message="Database timeout",
        ...     trace_id="abc-123"
        ... )
    """
    tool_name: str
    result: Any
    success: bool
    error_message: str = ""
    execution_time_ms: float = 0.0
    trace_id: str = ""
