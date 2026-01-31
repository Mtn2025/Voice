"""
Port (Interface) for tool execution.

Hexagonal Architecture: Domain defines contract, adapters implement.
Tools are isolated side-effects (DB queries, API calls, file I/O).

GAP Analysis Resolution: Gap #7 (Tool Calling Infrastructure)
Impact: Enables LLM function calling for database queries, external APIs
"""
from abc import ABC, abstractmethod

from app.domain.models.tool_models import ToolDefinition, ToolRequest, ToolResponse


class ToolPort(ABC):
    """
    Port for external tool execution.

    Hexagonal Architecture:
    - Domain (this file) defines the interface
    - Adapters (app/adapters/outbound/tools/*) implement concrete tools
    - Use Cases (app/domain/use_cases/execute_tool.py) orchestrate execution

    Example implementations:
    - DatabaseToolAdapter: Query application database
    - APIToolAdapter: Call external APIs
    - FileToolAdapter: Read/write files

    Example usage:
        >>> tool = DatabaseToolAdapter(session_factory)
        >>> request = ToolRequest(
        ...     tool_name="query_database",
        ...     arguments={"query": "John Smith"},
        ...     trace_id="abc-123"
        ... )
        >>> response = await tool.execute(request)
        >>> if response.success:
        ...     print(response.result)
    """

    @abstractmethod
    async def execute(self, request: ToolRequest) -> ToolResponse:
        """
        Execute tool with given arguments.

        This method should:
        1. Validate arguments against tool schema
        2. Execute side-effect (DB query, API call, etc.)
        3. Handle timeouts (respect request.timeout_seconds)
        4. Return ToolResponse with result or error

        Args:
            request: Tool execution request with arguments and context

        Returns:
            ToolResponse with result (if successful) or error message

        Raises:
            ToolExecutionError: Only for critical/unexpected errors
                               (most errors should return ToolResponse with success=False)

        Example:
            >>> async def execute(self, request):
            ...     try:
            ...         result = await self._do_work(request.arguments)
            ...         return ToolResponse(
            ...             tool_name=self.name,
            ...             result=result,
            ...             success=True
            ...         )
            ...     except Exception as e:
            ...         return ToolResponse(
            ...             tool_name=self.name,
            ...             result=None,
            ...             success=False,
            ...             error_message=str(e)
            ...         )
        """
        pass

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """
        Get tool metadata for LLM function calling.

        Returns tool schema in format compatible with:
        - OpenAI function calling
        - Groq function calling
        - Anthropic tool use

        Returns:
            ToolDefinition with name, description, parameters (JSON Schema)

        Example:
            >>> def get_definition(self):
            ...     return ToolDefinition(
            ...         name="query_database",
            ...         description="Search contact database for information",
            ...         parameters={
            ...             "query": {
            ...                 "type": "string",
            ...                 "description": "Search query (e.g. 'John Smith')"
            ...             },
            ...             "limit": {
            ...                 "type": "integer",
            ...                 "description": "Max results",
            ...                 "default": 5
            ...             }
            ...         },
            ...         required=["query"]
            ...     )
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique tool name identifier.

        This name is used:
        - In LLM function calling (LLM returns this name to invoke tool)
        - As registry key (ExecuteToolUseCase.tools[name])
        - In logs and metrics

        Convention: snake_case, descriptive, globally unique

        Returns:
            Tool name (e.g., "query_database", "fetch_property_price")

        Example:
            >>> @property
            >>> def name(self) -> str:
            ...     return "query_database"
        """
        pass
