import httpx
from typing import Optional

class HTTPClient:
    """
    Singleton wrapper for httpx.AsyncClient.
    Enables connection pooling (keep-alive) across the application.
    """
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """
        Get the shared AsyncClient instance.
        Must be initialized in main lifespan first.
        Fallback: If not initialized (e.g. tests), returns a temporary client? 
        No, strict singleton is better for consistency, but for safety lets create one if missing.
        However, creating one here means we don't manage its lifecycle (close).
        We should enforce lifecycle.
        """
        if cls._client is None:
            # Lazy init fallback (Warn in logs?)
            # Ideally main.py handles this.
            import logging
            logging.warning("⚠️ HTTPClient accessed before initialization! Creating unmanaged instance.")
            cls._client = httpx.AsyncClient()
        return cls._client

    @classmethod
    async def init(cls):
        """Initialize the client (Call in startup)."""
        if cls._client is None:
            cls._client = httpx.AsyncClient(timeout=30.0) # Reasonable default timeout

    @classmethod
    async def close(cls):
        """Close the client (Call in shutdown)."""
        if cls._client:
            await cls._client.aclose()
            cls._client = None

# Global Accessor
http_client = HTTPClient
