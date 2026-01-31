"""
Adaptador Redis Cache - Implementación de CachePort.

Wrappea el servicio de cache existente manteniendo la lógica
de serialización JSON y TTLs.
"""

import logging
from typing import Any

from app.domain.ports import CachePort
from app.services.cache import cache as redis_cache_service

logger = logging.getLogger(__name__)


class RedisCacheAdapter(CachePort):
    """
    Adaptador para Redis que implementa CachePort.

    Wrappea el servicio cache.py existente que ya maneja
    conexión lazy, serialización JSON, etc.
    """

    def __init__(self):
        # Use existing singleton cache service
        self._cache = redis_cache_service

    async def get(self, key: str) -> Any | None:
        """Obtiene valor del cache."""
        try:
            return await self._cache.get(key)
        except Exception as e:
            logger.warning(f"⚠️ [Redis Cache] Get failed for key '{key}': {e}")
            return None  # Graceful fallback

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Establece valor en cache con TTL."""
        try:
            await self._cache.set(key, value, ttl=ttl)
        except Exception as e:
            logger.warning(f"⚠️ [Redis Cache] Set failed for key '{key}': {e}")
            # Don't raise - cache failures shouldn't break app

    async def invalidate(self, pattern: str):
        """Invalida claves que coincidan con patrón."""
        try:
            await self._cache.invalidate(pattern)
        except Exception as e:
            logger.warning(f"⚠️ [Redis Cache] Invalidate failed for pattern '{pattern}': {e}")

    async def close(self):
        """Cierra conexión a Redis."""
        try:
            await self._cache.close()
        except Exception as e:
            logger.warning(f"⚠️ [Redis Cache] Close failed: {e}")
