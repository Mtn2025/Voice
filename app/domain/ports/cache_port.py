"""
Puerto (Interface) para cache distribuido.

Abstrae Redis u otro sistema de cache para el dominio.
"""

from abc import ABC, abstractmethod
from typing import Any


class CachePort(ABC):
    """
    Puerto para cache distribuido.

    Implementaciones: RedisCacheAdapter, MemoryCacheAdapter (tests)
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Obtiene valor del cache.

        Args:
            key: Clave del cache

        Returns:
            Valor deserializado o None si no existe
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Establece valor en cache.

        Args:
            key: Clave
            value: Valor (será serializado a JSON)
            ttl: Tiempo de vida en segundos (default 1h)
        """
        pass

    @abstractmethod
    async def invalidate(self, pattern: str):
        """
        Invalida claves que coincidan con patrón.

        Args:
            pattern: Patrón glob (ej: "voices_*")
        """
        pass

    @abstractmethod
    async def close(self):
        """Cierra conexión a cache."""
        pass
