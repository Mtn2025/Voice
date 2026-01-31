"""
LLM Domain Models - Function Calling Support.

Enables LLM to request tool execution via function_call mechanism.
"""
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMFunctionCall:
    """
    Function call emitted by LLM.

    Represents LLM's desire to execute a tool/function with specific arguments.

    Attributes:
        name: Tool/function name to execute
        arguments: Tool arguments (parsed JSON dict)
        call_id: Optional call ID for tracking (OpenAI format)

    Example:
        >>> function_call = LLMFunctionCall(
        ...     name="query_database",
        ...     arguments={"query": "John Smith", "limit": 5}
        ... )
        >>> print(function_call.name)
        'query_database'
    """
    name: str
    arguments: dict[str, Any]
    call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Export to dictionary format."""
        return {
            "name": self.name,
            "arguments": self.arguments,
            "call_id": self.call_id
        }

    @classmethod
    def from_openai_format(cls, tool_call: Any) -> "LLMFunctionCall":
        """
        Parse from OpenAI/Groq tool_call format.

        Args:
            tool_call: Tool call object from LLM response

        Returns:
            LLMFunctionCall instance
        """
        arguments = tool_call.function.arguments

        # Defensive Parsing: Handle string vs dict automatically
        if isinstance(arguments, str):
            try:
                parsed_args = json.loads(arguments)
            except json.JSONDecodeError:
                # Fallback if args are malformed
                parsed_args = {}
        elif isinstance(arguments, dict):
             parsed_args = arguments
        else:
             parsed_args = {}

        return cls(
            name=tool_call.function.name,
            arguments=parsed_args,
            call_id=getattr(tool_call, 'id', None)
        )


@dataclass
class LLMChunk:
    """
    Single chunk from LLM streaming response.

    Can contain either:
    - Text content (normal response)
    - Function call (tool execution request)
    - Both (rare, but possible in some providers)

    Attributes:
        text: Text content chunk
        function_call: Function call request
        finish_reason: Why stream ended ("stop", "function_call", "length", etc.)
        metadata: Additional metadata (e.g., token usage, model info)
    """
    text: str | None = None
    function_call: LLMFunctionCall | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_text(self) -> bool:
        """Check if chunk contains text."""
        return self.text is not None and len(self.text) > 0

    @property
    def has_function_call(self) -> bool:
        """Check if chunk contains function call."""
        return self.function_call is not None

    @property
    def is_complete(self) -> bool:
        """Check if this is the final chunk (has finish_reason)."""
        return self.finish_reason is not None


@dataclass
class ToolDefinitionForLLM:
    """
    Tool definition formatted for LLM function calling.

    Converts domain ToolDefinition to LLM-compatible format.
    """
    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai_format(self) -> dict[str, Any]:
        """
        Export to OpenAI/Groq function calling format.

        Returns:
            Dict compatible with OpenAI tools API
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
