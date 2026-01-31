"""
Database Tool Adapter - Query application database.

Hexagonal Architecture: Adapter implements ToolPort interface.
Isolated side-effect for database queries during LLM conversations.

Example use cases:
- Search contacts by name/phone
- Get campaign statistics
- Retrieve user preferences
"""
import logging
import time
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.tool_models import ToolDefinition, ToolRequest, ToolResponse
from app.domain.ports.tool_port import ToolPort

logger = logging.getLogger(__name__)


class DatabaseToolAdapter(ToolPort):
    """
    Tool for querying application database.

    Implements ToolPort interface for database access.
    Executes SQL queries in isolated async session.

    Example:
        >>> from app.infrastructure.database import get_session_factory
        >>> session_factory = get_session_factory()
        >>> db_tool = DatabaseToolAdapter(session_factory)
        >>>
        >>> request = ToolRequest(
        ...     tool_name="query_database",
        ...     arguments={"query": "John Smith", "limit": 5},
        ...     trace_id="abc-123"
        ... )
        >>> response = await db_tool.execute(request)
        >>> print(response.result)
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]):
        """
        Initialize database tool.

        Args:
            session_factory: Async SQLAlchemy session factory
                           (e.g., from app.infrastructure.database)
        """
        self._session_factory = session_factory
        self._name = "query_database"

    @property
    def name(self) -> str:
        """Unique tool name identifier."""
        return self._name

    def get_definition(self) -> ToolDefinition:
        """
        Get tool metadata for LLM function calling.

        Returns:
            ToolDefinition with schema for database queries
        """
        return ToolDefinition(
            name=self._name,
            description=(
                "Search the contact database for information. "
                "Use natural language queries to find contacts, campaigns, or statistics."
            ),
            parameters={
                "query": {
                    "type": "string",
                    "description": (
                        "Natural language search query "
                        "(e.g., 'find contact John Smith', 'get campaign stats for last week')"
                    )
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5
                }
            },
            required=["query"]
        )

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """
        Execute database query.

        Args:
            request: Tool execution request with query parameters

        Returns:
            ToolResponse with query results or error
        """
        start_time = time.time()
        trace_id = request.trace_id

        try:
            # Extract arguments
            query = request.arguments.get("query", "")
            limit = request.arguments.get("limit", 5)

            if not query:
                return ToolResponse(
                    tool_name=self._name,
                    result=None,
                    success=False,
                    error_message="Missing required argument: 'query'",
                    trace_id=trace_id
                )

            logger.info(
                f"[Tool DB] trace={trace_id} Executing query: '{query[:100]}' (limit={limit})"
            )

            # Execute query in async session
            async with self._session_factory() as session:
                result = await self._search_contacts(session, query, limit)

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                f"[Tool DB] trace={trace_id} Success - "
                f"found {len(result) if result else 0} results in {execution_time:.0f}ms"
            )

            return ToolResponse(
                tool_name=self._name,
                result=result,
                success=True,
                execution_time_ms=execution_time,
                trace_id=trace_id
            )

        except TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"[Tool DB] trace={trace_id} Timeout after {execution_time:.0f}ms")

            return ToolResponse(
                tool_name=self._name,
                result=None,
                success=False,
                error_message=f"Database query timeout ({execution_time:.0f}ms)",
                execution_time_ms=execution_time,
                trace_id=trace_id
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"[Tool DB] trace={trace_id} Error: {e}", exc_info=True)

            return ToolResponse(
                tool_name=self._name,
                result=None,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                trace_id=trace_id
            )

    async def _search_contacts(
        self,
        session: AsyncSession,
        query: str,
        limit: int
    ) -> list:
        """
        Search contacts matching query.

        Args:
            session: Async SQLAlchemy session
            query: Natural language search query
            limit: Maximum results

        Returns:
            List of matching contacts

        TODO: Implement actual DB search logic with:
        - Full-text search on contacts.name, contacts.phone
        - Fuzzy matching for partial names
        - Campaign statistics aggregation
        """
        # For now, return mock result
        # In production, this would execute actual SQL queries

        logger.debug(f"[DatabaseToolAdapter] Searching for: {query} (limit={limit})")

        # Mock implementation
        mock_results = [
            {"id": 1, "name": "John Smith", "phone": "+1234567890", "email": "john@example.com"},
            {"id": 2, "name": "Jane Doe", "phone": "+0987654321", "email": "jane@example.com"},
            {"id": 3, "name": "Bob Johnson", "phone": "+1122334455", "email": "bob@example.com"}
        ]

        # Filter by query (simple contains check for mock)
        query_lower = query.lower()
        filtered = [
            contact for contact in mock_results
            if query_lower in contact["name"].lower() or query_lower in contact["phone"]
        ]

        return filtered[:limit]


# Import asyncio for timeout handling
