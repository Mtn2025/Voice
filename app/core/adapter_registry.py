"""
AdapterRegistry - Module 15 (Hot-Swap Adapters).

Enables runtime adapter swapping for debugging and A/B testing.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Registry for runtime adapter management and swapping.
    
    Enables:
    - Runtime adapter replacement (debugging)
    - A/B testing (swap between providers)
    - Graceful degradation (swap to fallback)
    
    Example:
        >>> registry = AdapterRegistry()
        >>> 
        >>> # Register adapters
        >>> registry.register("tts", AzureTTSAdapter())
        >>> registry.register("stt", AzureSTTAdapter())
        >>> 
        >>> # Runtime swap (e.g., for debugging)
        >>> registry.swap("tts", GoogleTTSAdapter())
        >>> 
        >>> # Get current adapter
        >>> tts = registry.get("tts")  # Returns GoogleTTSAdapter
    """
    
    def __init__(self):
        """Initialize empty adapter registry."""
        self._adapters: Dict[str, Any] = {}
        logger.info("[AdapterRegistry] Initialized")
    
    def register(self, name: str, adapter: Any):
        """
        Register an adapter.
        
        Args:
            name: Adapter name (e.g., "tts", "stt", "llm")
            adapter: Adapter instance
        
        Example:
            >>> registry.register("tts", AzureTTSAdapter())
        """
        if name in self._adapters:
            logger.warning(
                f"[AdapterRegistry] Overwriting existing adapter: {name} "
                f"(was: {type(self._adapters[name]).__name__})"
            )
        
        self._adapters[name] = adapter
        logger.info(
            f"[AdapterRegistry] Registered: {name} → {type(adapter).__name__}"
        )
    
    def swap(self, name: str, new_adapter: Any):
        """
        Swap adapter at runtime.
        
        Args:
            name: Adapter name to swap
            new_adapter: New adapter instance
        
        Raises:
            KeyError: If adapter name not registered
        
        Example:
            >>> # Swap TTS from Azure to Google
            >>> registry.swap("tts", GoogleTTSAdapter())
        """
        if name not in self._adapters:
            raise KeyError(
                f"[AdapterRegistry] Cannot swap: '{name}' not registered. "
                f"Available: {list(self._adapters.keys())}"
            )
        
        old_adapter = self._adapters[name]
        self._adapters[name] = new_adapter
        
        logger.warning(
            f"[AdapterRegistry] 🔄 SWAPPED: {name} - "
            f"{type(old_adapter).__name__} → {type(new_adapter).__name__}"
        )
    
    def get(self, name: str) -> Any:
        """
        Get current adapter.
        
        Args:
            name: Adapter name
        
        Returns:
            Current adapter instance
        
        Raises:
            KeyError: If adapter not registered
        """
        if name not in self._adapters:
            raise KeyError(
                f"[AdapterRegistry] Adapter '{name}' not found. "
                f"Available: {list(self._adapters.keys())}"
            )
        
        return self._adapters[name]
    
    def list_adapters(self) -> Dict[str, str]:
        """
        List all registered adapters.
        
        Returns:
            Dict mapping adapter names to class names
        
        Example:
            >>> registry.list_adapters()
            {'tts': 'AzureTTSAdapter', 'stt': 'AzureSTTAdapter', 'llm': 'GroqLLMAdapter'}
        """
        return {
            name: type(adapter).__name__
            for name, adapter in self._adapters.items()
        }
    
    def unregister(self, name: str):
        """
        Unregister an adapter.
        
        Args:
            name: Adapter name to remove
        """
        if name in self._adapters:
            adapter_type = type(self._adapters[name]).__name__
            del self._adapters[name]
            logger.info(f"[AdapterRegistry] Unregistered: {name} ({adapter_type})")
        else:
            logger.warning(f"[AdapterRegistry] Cannot unregister: '{name}' not found")
