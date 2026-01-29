"""
Fallback Wrapper for LLM Port - Graceful Degradation.

Implements automatic failover between multiple LLM providers.
"""
import logging
from typing import AsyncIterator
from app.domain.ports import LLMPort, LLMRequest, LLMException


logger = logging.getLogger(__name__)


class LLMWithFallback(LLMPort):
    """
    LLM Port wrapper with graceful degradation.
    
    Attempts primary provider first, falls back to secondary providers
    on retryable failures.
    """
    
    def __init__(self, primary: LLMPort, fallbacks: list[LLMPort]):
        """
        Args:
            primary: Primary LLM provider (e.g., Groq)
            fallbacks: Ordered list of fallback providers
        """
        self.primary = primary
        self.fallbacks = fallbacks
    
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """
        Generate stream from primary, fallback on retryable failures.
        """
        # Try primary first
        try:
            logger.info("[LLM Fallback] Attempting primary provider")
            async for chunk in self.primary.generate_stream(request):
                yield chunk
            return  # Success - no fallback needed
        
        except LLMException as e:
            if not e.retryable or not self.fallbacks:
                # Non-retryable or no fallbacks available
                raise
            
            logger.warning(
                f"[LLM Fallback] Primary failed (retryable): {e}. "
                f"Trying {len(self.fallbacks)} fallback(s)..."
            )
        
        # Try fallbacks
        for i, fallback in enumerate(self.fallbacks):
            try:
                logger.info(f"[LLM Fallback] Attempting fallback {i+1}/{len(self.fallbacks)}")
                async for chunk in fallback.generate_stream(request):
                    yield chunk
                return  # Success
            
            except LLMException as e:
                if i == len(self.fallbacks) - 1:
                    # Last fallback failed - propagate error
                    logger.error(f"[LLM Fallback] All providers failed")
                    raise
                
                # Try next fallback
                logger.warning(f"[LLM Fallback] Fallback {i+1} failed: {e}")
                continue
    
    async def get_available_models(self) -> list[str]:
        """Get models from primary provider."""
        return await self.primary.get_available_models()

    async def is_model_safe_for_voice(self, model: str) -> bool:
        """Check if model is safe for voice from primary provider."""
        return await self.primary.is_model_safe_for_voice(model)
