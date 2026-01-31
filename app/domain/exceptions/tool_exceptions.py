"""
Domain exceptions for tool execution.

Hexagonal Architecture: Domain defines its own exceptions,
independent of infrastructure implementation details.
"""


class ToolExecutionError(Exception):
    """
    Base exception for tool execution errors.

    Attributes:
        tool_name: Name of the tool that failed
        message: Error description
        retryable: Whether the error is transient and retryable

    Example:
        >>> raise ToolExecutionError(
        ...     tool_name="query_database",
        ...     message="Connection timeout",
        ...     retryable=True
        ... )
    """

    def __init__(self, tool_name: str, message: str, retryable: bool = False):
        self.tool_name = tool_name
        self.message = message
        self.retryable = retryable
        super().__init__(f"Tool '{tool_name}' error: {message}")


class ToolTimeoutError(ToolExecutionError):
    """
    Tool execution exceeded timeout.

    This is typically retryable if the external service is temporarily slow.

    Example:
        >>> raise ToolTimeoutError(
        ...     tool_name="fetch_property_price",
        ...     timeout=10.0
        ... )
    """

    def __init__(self, tool_name: str, timeout: float):
        super().__init__(
            tool_name,
            f"Execution timeout after {timeout}s",
            retryable=True
        )
        self.timeout = timeout


class ToolNotFoundError(ToolExecutionError):
    """
    Requested tool does not exist in registry.

    This is NOT retryable - indicates programming error or misconfiguration.

    Example:
        >>> raise ToolNotFoundError(tool_name="nonexistent_tool")
    """

    def __init__(self, tool_name: str, available_tools: list | None = None):
        available = f". Available: {available_tools}" if available_tools else ""
        super().__init__(
            tool_name,
            f"Tool '{tool_name}' not found in registry{available}",
            retryable=False
        )
        self.available_tools = available_tools or []


class ToolValidationError(ToolExecutionError):
    """
    Tool arguments failed validation.

    NOT retryable - indicates incorrect LLM function call.

    Example:
        >>> raise ToolValidationError(
        ...     tool_name="query_database",
        ...     message="Missing required argument: 'query'"
        ... )
    """

    def __init__(self, tool_name: str, message: str):
        super().__init__(
            tool_name,
            f"Validation failed: {message}",
            retryable=False
        )
