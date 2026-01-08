"""
Redis State Manager - Punto A9

Manages call state in Redis for horizontal scalability.
Allows multiple app instances to share Telnyx call state.
"""

import json
import logging
from typing import Any

try:
    import redis.asyncio as redis
    from redis.exceptions import RedisError as PyRedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    # Dummy exception for when redis is not installed to avoid NameError in except blocks
    class PyRedisError(Exception):
        pass

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisStateManager:
    """Manage call state in Redis for horizontal scaling."""

    def __init__(self):
        """Initialize Redis connection pool."""
        self.redis: Any | None = None
        self._enabled = False
        self._fallback_storage: dict[str, dict[str, Any]] = {}

    async def connect(self):
        """Establish Redis connection. Falls back to in-memory if unavailable."""
        if not REDIS_AVAILABLE:
            logger.warning("⚠️ redis library not installed. Using in-memory fallback (not scalable)")
            logger.warning("   Install with: pip install 'redis[hiredis]==5.0.1'")
            self._enabled = False
            return

        try:
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self.redis.ping()
            self._enabled = True
            logger.info("✅ [REDIS] Connected - Horizontal scaling enabled")
        except PyRedisError as e:
            logger.error(f"❌ [REDIS] Connection failed: {e}")
            logger.warning("⚠️ [REDIS] Falling back to in-memory state (NOT scalable)")
            self._enabled = False
        except Exception as e:
            # Capture unexpected errors during init (e.g. config errors)
            logger.error(f"❌ [REDIS] Unexpected initialization error: {e}", exc_info=True)
            self._enabled = False

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis and self._enabled:
            try:
                await self.redis.close()
                logger.info("✅ [REDIS] Disconnected")
            except PyRedisError as e:
                logger.error(f"❌ [REDIS] Error during disconnect: {e}")

    async def set_call(self, call_id: str, data: dict[str, Any], ttl: int = 3600):
        """Store call state with TTL (default 1 hour)."""
        if self._enabled and self.redis:
            try:
                key = f"call:{call_id}"
                value = json.dumps(data)
                await self.redis.setex(key, ttl, value)
                logger.debug(f"✅ [REDIS] Stored call: {call_id}")
            except PyRedisError as e:
                logger.error(f"❌ [REDIS] Failed to store call: {e}")
                self._fallback_storage[call_id] = data
            except (TypeError, ValueError) as e:
                 logger.error(f"❌ [REDIS] Serialization error for call {call_id}: {e}")
                 # Critical: Logic error, but fallback safe
                 self._fallback_storage[call_id] = data
        else:
            self._fallback_storage[call_id] = data

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        """Retrieve call state."""
        if self._enabled and self.redis:
            try:
                key = f"call:{call_id}"
                value = await self.redis.get(key)
                if value:
                    return json.loads(value)
                return None
            except PyRedisError as e:
                logger.error(f"❌ [REDIS] Failed to get call: {e}")
                return self._fallback_storage.get(call_id)
            except json.JSONDecodeError as e:
                 logger.error(f"❌ [REDIS] Data corruption for call {call_id}: {e}")
                 return None
        else:
            return self._fallback_storage.get(call_id)

    async def delete_call(self, call_id: str):
        """Remove call state."""
        if self._enabled and self.redis:
            try:
                key = f"call:{call_id}"
                await self.redis.delete(key)
                logger.debug(f"🗑️ [REDIS] Deleted call: {call_id}")
            except PyRedisError as e:
                logger.error(f"❌ [REDIS] Failed to delete call: {e}")
                self._fallback_storage.pop(call_id, None)
        else:
            self._fallback_storage.pop(call_id, None)

    async def call_exists(self, call_id: str) -> bool:
        """Check if call exists."""
        if self._enabled and self.redis:
            try:
                key = f"call:{call_id}"
                exists = await self.redis.exists(key)
                return bool(exists)
            except PyRedisError as e:
                logger.error(f"❌ [REDIS] Failed to check existence: {e}")
                return call_id in self._fallback_storage
        else:
            return call_id in self._fallback_storage

    async def cache_get(self, key: str) -> dict | None:
        """Generic cache get (JSON). Key will be prefixed with 'cache:'."""
        if self._enabled and self.redis:
            try:
                full_key = f"cache:{key}"
                value = await self.redis.get(full_key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"⚠️ [REDIS-CACHE] Get failed for {key}: {e}")
        return None

    async def cache_set(self, key: str, value: Any, ttl: int = 3600):
        """Generic cache set (JSON). Key will be prefixed with 'cache:'."""
        if self._enabled and self.redis:
            try:
                full_key = f"cache:{key}"
                payload = json.dumps(value)
                await self.redis.setex(full_key, ttl, payload)
            except Exception as e:
                logger.warning(f"⚠️ [REDIS-CACHE] Set failed for {key}: {e}")

    @property
    def is_redis_enabled(self) -> bool:
        """Check if Redis is enabled."""
        return self._enabled


# Global singleton
redis_state = RedisStateManager()
