"""
API Tool Adapter - Call external APIs.

Hexagonal Architecture: Adapter implements ToolPort interface.
Isolated side-effect for external API calls during LLM conversations.

Example use cases:
- Property price lookup from MLS API
- Weather data from external service
- Currency conversion rates
"""
import asyncio
import logging
import time

import aiohttp

from app.domain.models.tool_models import ToolDefinition, ToolRequest, ToolResponse
from app.domain.ports.tool_port import ToolPort

logger = logging.getLogger(__name__)


class APIToolAdapter(ToolPort):
    """
    Tool for calling external APIs.

    Implements ToolPort interface for HTTP API access.
    Executes GET/POST requests with timeout handling.

    Example:
        >>> api_tool = APIToolAdapter(
        ...     api_base_url="https://api.example.com",
        ...     api_key="your-api-key"
        ... )
        >>>
        >>> request = ToolRequest(
        ...     tool_name="fetch_property_price",
        ...     arguments={"address": "123 Main St, New York, NY"},
        ...     trace_id="abc-123",
        ...     timeout_seconds=10.0
        ... )
        >>> response = await api_tool.execute(request)
        >>> print(response.result)
    """

    def __init__(
        self,
        api_base_url: str,
        api_key: str | None = None,
        tool_name: str = "fetch_property_price"
    ):
        """
        Initialize API tool.

        Args:
            api_base_url: Base URL for API (e.g., "https://api.example.com")
            api_key: Optional API key for authentication
            tool_name: Unique tool identifier (default: "fetch_property_price")
        """
        self._api_base_url = api_base_url.rstrip('/')
        self._api_key = api_key
        self._name = tool_name

    @property
    def name(self) -> str:
        """Unique tool name identifier."""
        return self._name

    def get_definition(self) -> ToolDefinition:
        """
        Get tool metadata for LLM function calling.

        Returns:
            ToolDefinition with schema for API calls
        """
        return ToolDefinition(
            name=self._name,
            description=(
                "Get current market price for a property address from real estate database. "
                "Provides estimated property value based on recent comparable sales."
            ),
            parameters={
                "address": {
                    "type": "string",
                    "description": (
                        "Full property address including street, city, state, and zip code "
                        "(e.g., '123 Main St, New York, NY 10001')"
                    )
                }
            },
            required=["address"]
        )

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """
        Execute external API call.

        Args:
            request: Tool execution request with API parameters

        Returns:
            ToolResponse with API result or error
        """
        start_time = time.time()
        trace_id = request.trace_id

        try:
            # Extract arguments
            address = request.arguments.get("address", "")

            if not address:
                return ToolResponse(
                    tool_name=self._name,
                    result=None,
                    success=False,
                    error_message="Missing required argument: 'address'",
                    trace_id=trace_id
                )

            logger.info(
                f"[Tool API] trace={trace_id} Fetching property price for: '{address[:100]}'"
            )

            # Execute API call with timeout
            result = await asyncio.wait_for(
                self._fetch_property_data(address),
                timeout=request.timeout_seconds
            )

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                f"[Tool API] trace={trace_id} Success - "
                f"fetched data in {execution_time:.0f}ms"
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
            logger.error(
                f"[Tool API] trace={trace_id} Timeout after {execution_time:.0f}ms"
            )

            return ToolResponse(
                tool_name=self._name,
                result=None,
                success=False,
                error_message=f"API call timeout ({request.timeout_seconds}s)",
                execution_time_ms=execution_time,
                trace_id=trace_id
            )

        except aiohttp.ClientError as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"[Tool API] trace={trace_id} HTTP Error: {e}")

            return ToolResponse(
                tool_name=self._name,
                result=None,
                success=False,
                error_message=f"API request failed: {e!s}",
                execution_time_ms=execution_time,
                trace_id=trace_id
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"[Tool API] trace={trace_id} Error: {e}", exc_info=True)

            return ToolResponse(
                tool_name=self._name,
                result=None,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                trace_id=trace_id
            )

    async def _fetch_property_data(self, address: str) -> dict:
        """
        Fetch property data from external API.

        Args:
            address: Property address to query

        Returns:
            Dictionary with property data

        Raises:
            aiohttp.ClientError: If HTTP request fails

        TODO: Replace with actual API integration
        """
        logger.debug(f"[APIToolAdapter] Fetching data for: {address}")

        # Mock implementation for demonstration
        # In production, this would call real estate API

        # Build request headers (if needed in future)
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        # For mock, simulate API delay
        await asyncio.sleep(0.1)  # Simulate 100ms API latency

        # Mock response
        # TODO: Replace with actual API call:
        # async with aiohttp.ClientSession() as session:
        #     params = {"address": address}
        #     async with session.get(f"{self._api_base_url}/property/price", params=params, headers=headers) as resp:
        #         return await resp.json()
        mock_response = {
            "address": address,
            "estimated_value": 450000,
            "currency": "USD",
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 2100
        }

        return mock_response
