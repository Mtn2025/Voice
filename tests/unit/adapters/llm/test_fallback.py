"""
Unit tests for Fallback Integration - Module 6.

Validates LLMWithFallback wrapper functionality.
Tests primary provider success, fallback on retryable errors.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock
from app.domain.ports import LLMPort, LLMRequest, LLMMessage, LLMException
from app.adapters.outbound.llm.llm_with_fallback import LLMWithFallback


class MockLLMAdapter(LLMPort):
    """Mock LLM adapter for testing."""
    
    def __init__(self, name: str, should_fail: bool = False, retryable: bool = True):
        self.name = name
        self.should_fail = should_fail
        self.retryable = retryable
        self.call_count = 0
    
    async def generate_stream(self, request: LLMRequest):
        """Generate mock stream or raise exception."""
        self.call_count += 1
        
        if self.should_fail:
            raise LLMException(
                f"{self.name} failed",
                retryable=self.retryable,
                provider=self.name
            )
        
        # Success - yield tokens
        for token in [f"{self.name}-", "response"]:
            yield token
    
    async def get_available_models(self):
        return [f"{self.name}-model-1"]
    
    async def is_model_safe_for_voice(self, model: str) -> bool:
        """Check if model is safe for voice streaming."""
        return True  # Mock - always safe


class TestFallbackIntegration:
    """Test suite for LLM fallback mechanism."""
    
    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self):
        """When primary succeeds, fallback should not be called."""
        primary = MockLLMAdapter("groq", should_fail=False)
        fallback1 = MockLLMAdapter("openai", should_fail=False)
        
        wrapper = LLMWithFallback(primary=primary, fallbacks=[fallback1])
        
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="test-model"
        )
        
        # Collect response
        response_tokens = []
        async for token in wrapper.generate_stream(request):
            response_tokens.append(token)
        
        # Primary should be called
        assert primary.call_count == 1
        # Fallback should NOT be called
        assert fallback1.call_count == 0
        # Response should be from primary
        assert "groq" in ''.join(response_tokens)
    
    @pytest.mark.asyncio
    async def test_primary_fails_fallback_succeeds(self):
        """When primary fails (retryable), fallback should be used."""
        primary = MockLLMAdapter("groq", should_fail=True, retryable=True)
        fallback1 = MockLLMAdapter("openai", should_fail=False)
        
        wrapper = LLMWithFallback(primary=primary, fallbacks=[fallback1])
        
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="test-model"
        )
        
        # Collect response
        response_tokens = []
        async for token in wrapper.generate_stream(request):
            response_tokens.append(token)
        
        # Both should be called
        assert primary.call_count == 1
        assert fallback1.call_count == 1
        # Response should be from fallback
        assert "openai" in ''.join(response_tokens)
    
    @pytest.mark.asyncio
    async def test_primary_fails_nonretryable_no_fallback(self):
        """When primary fails (non-retryable), error should propagate."""
        primary = MockLLMAdapter("groq", should_fail=True, retryable=False)
        fallback1 = MockLLMAdapter("openai", should_fail=False)
        
        wrapper = LLMWithFallback(primary=primary, fallbacks=[fallback1])
        
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="test-model"
        )
        
        # Should raise exception
        with pytest.raises(LLMException) as exc:
            async for _ in wrapper.generate_stream(request):
                pass
        
        assert "groq failed" in str(exc.value)
        # Fallback should NOT be called
        assert fallback1.call_count == 0
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """When all providers fail, error should propagate."""
        primary = MockLLMAdapter("groq", should_fail=True, retryable=True)
        fallback1 = MockLLMAdapter("openai", should_fail=True, retryable=True)
        fallback2 = MockLLMAdapter("claude", should_fail=True, retryable=True)
        
        wrapper = LLMWithFallback(primary=primary, fallbacks=[fallback1, fallback2])
        
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="test-model"
        )
        
        # Should raise exception
        with pytest.raises(LLMException):
            async for _ in wrapper.generate_stream(request):
                pass
        
        # All should be called
        assert primary.call_count == 1
        assert fallback1.call_count == 1
        assert fallback2.call_count == 1
    
    @pytest.mark.asyncio
    async def test_second_fallback_succeeds(self):
        """First fallback fails, second succeeds."""
        primary = MockLLMAdapter("groq", should_fail=True, retryable=True)
        fallback1 = MockLLMAdapter("openai", should_fail=True, retryable=True)
        fallback2 = MockLLMAdapter("claude", should_fail=False)
        
        wrapper = LLMWithFallback(primary=primary, fallbacks=[fallback1, fallback2])
        
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="test-model"
        )
        
        # Collect response
        response_tokens = []
        async for token in wrapper.generate_stream(request):
            response_tokens.append(token)
        
        # All should be called up to second fallback
        assert primary.call_count == 1
        assert fallback1.call_count == 1
        assert fallback2.call_count == 1
        # Response should be from second fallback
        assert "claude" in ''.join(response_tokens)
    
    @pytest.mark.asyncio
    async def test_get_available_models_from_primary(self):
        """get_available_models should use primary provider."""
        primary = MockLLMAdapter("groq")
        fallback1 = MockLLMAdapter("openai")
        
        wrapper = LLMWithFallback(primary=primary, fallbacks=[fallback1])
        
        models = await wrapper.get_available_models()
        assert "groq-model-1" in models


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
