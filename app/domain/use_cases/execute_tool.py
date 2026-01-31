"""
Execute Tool Use Case - Domain logic for tool orchestration.

Hexagonal Architecture: Domain use case coordinates tool execution.
Independent of infrastructure (adapters, frameworks).
"""
import logging

from app.domain.models.tool_models import ToolDefinition, ToolRequest, ToolResponse
from app.domain.ports.tool_port import ToolPort

logger = logging.getLogger(__name__)


class ExecuteToolUseCase:
    """
    Domain use case for executing tools.

    Coordinates tool execution, validates tool existence,
    handles errors, and logs metrics.

    Hexagonal Architecture:
    - Use Case is in Domain layer (pure business logic)
    - Depends on ToolPort interface (not concrete adapters)
    - Orchestrates multiple tools via dependency injection
    """

    def __init__(self, tools: dict[str, ToolPort]):
        """
        Initialize use case with available tools.

        Args:
            tools: Dictionary mapping tool_name -> ToolPort instance
        """
        self.tools = tools
        logger.info(
            f"[ExecuteToolUseCase] Initialized with {len(tools)} tools: "
            f"{list(tools.keys())}"
        )

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """
        Execute requested tool.

        Validates tool exists, executes it, and logs results.

        Args:
            request: Tool execution request with tool_name and arguments

        Returns:
            ToolResponse with result or error
        """
        trace_id = request.trace_id
        tool_name = request.tool_name

        # Validate tool exists
        if tool_name not in self.tools:
            available_tools = list(self.tools.keys())
            logger.error(
                f"[ExecuteToolUseCase] trace={trace_id} "
                f"Tool '{tool_name}' not found. Available: {available_tools}"
            )

            return ToolResponse(
                tool_name=tool_name,
                result=None,
                success=False,
                error_message=(
                    f"Tool '{tool_name}' not found. "
                    f"Available tools: {', '.join(available_tools)}"
                ),
                trace_id=trace_id
            )

        # Execute tool
        tool = self.tools[tool_name]

        logger.info(
            f"[ExecuteToolUseCase] trace={trace_id} "
            f"Executing tool '{tool_name}' with args: {request.arguments}"
        )

        try:
            response = await tool.execute(request)
        except Exception as e:
            # Catch any unexpected exceptions from adapter
            logger.error(
                f"[ExecuteToolUseCase] trace={trace_id} "
                f"Tool '{tool_name}' raised unexpected exception: {e}",
                exc_info=True
            )

            return ToolResponse(
                tool_name=tool_name,
                result=None,
                success=False,
                error_message=f"Unexpected tool error: {e!s}",
                trace_id=trace_id
            )

        # Log result
        if response.success:
            logger.info(
                f"[ExecuteToolUseCase] trace={trace_id} "
                f"Tool '{tool_name}' SUCCESS - {response.execution_time_ms:.0f}ms"
            )
        else:
            logger.warning(
                f"[ExecuteToolUseCase] trace={trace_id} "
                f"Tool '{tool_name}' FAILED - {response.error_message}"
            )

        return response

    def get_tool_definitions(self) -> list[ToolDefinition]:
        """
        Get all tool definitions for LLM function calling.

        Exports tool schemas in format compatible with:
        - OpenAI function calling
        - Groq function calling
        - Anthropic tool use

        Returns:
            List of ToolDefinition objects with schemas
        """
        definitions = [tool.get_definition() for tool in self.tools.values()]

        logger.debug(
            f"[ExecuteToolUseCase] Exported {len(definitions)} tool definitions"
        )

        return definitions

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if tool is registered.

        Args:
            tool_name: Tool identifier to check

        Returns:
            True if tool exists, False otherwise
        """
        return tool_name in self.tools

    @property
    def tool_count(self) -> int:
        """Number of registered tools."""
        return len(self.tools)
