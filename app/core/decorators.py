"""
Performance Decorators - P3 (Observability)

Track latency metrics (TTFB) per port/adapter.
"""
import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def track_latency(port_name: str) -> Callable:
    """
    Decorator to track Time-To-First-Byte (TTFB) latency for ports.
    
    Args:
        port_name: Name of the port/adapter (e.g., "groq_llm", "azure_tts", "azure_stt")
    
    Usage:
        @track_latency("groq_llm")
        async def generate_stream(self, request: LLMRequest):
            ...
    
    Logs:
        [Metrics] groq_llm.ttfb=245.32ms (request_id=abc123)
    
    Example:
        >>> class MyAdapter:
        ...     @track_latency("my_service")
        ...     async def call_api(self):
        ...         await asyncio.sleep(0.1)
        >>> # Logs: [Metrics] my_service.ttfb=100.00ms
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Calculate TTFB
                ttfb_ms = (time.time() - start_time) * 1000
                
                # Extract request ID if available
                request_id = "unknown"
                if args and len(args) > 1:
                    request_obj = args[1]  # Typically request is 2nd param (after self)
                    if hasattr(request_obj, 'trace_id'):
                        request_id = request_obj.trace_id[:8]  # First 8 chars
                
                # Log metrics
                logger.info(
                    f"📊 [Metrics] {port_name}.ttfb={ttfb_ms:.2f}ms "
                    f"(request_id={request_id})"
                )
                
                return result
                
            except Exception as e:
                # Track failures too
                ttfb_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"❌ [Metrics] {port_name}.ttfb={ttfb_ms:.2f}ms "
                    f"(FAILED: {type(e).__name__})"
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                ttfb_ms = (time.time() - start_time) * 1000
                
                logger.info(f"📊 [Metrics] {port_name}.ttfb={ttfb_ms:.2f}ms")
                return result
                
            except Exception as e:
                ttfb_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"❌ [Metrics] {port_name}.ttfb={ttfb_ms:.2f}ms "
                    f"(FAILED: {type(e).__name__})"
                )
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def track_streaming_latency(port_name: str) -> Callable:
    """
    Decorator to track streaming latency (TTFB for first chunk).
    
    Args:
        port_name: Name of the streaming port
    
    Usage:
        @track_streaming_latency("groq_llm_stream")
        async def generate_stream(self, request):
            async for chunk in stream:
                yield chunk
    
    Tracks:
        - TTFB: Time to first chunk
        - Total duration: Time to last chunk
        - Chunks count
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            ttfb_logged = False
            chunk_count = 0
            
            try:
                async for chunk in func(*args, **kwargs):
                    chunk_count += 1
                    
                    # Log TTFB on first chunk
                    if not ttfb_logged:
                        ttfb_ms = (time.time() - start_time) * 1000
                        logger.info(
                            f"📊 [Metrics] {port_name}.ttfb={ttfb_ms:.2f}ms (streaming)"
                        )
                        ttfb_logged = True
                    
                    yield chunk
                
                # Log total duration
                total_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"📊 [Metrics] {port_name}.total_duration={total_ms:.2f}ms "
                    f"(chunks={chunk_count})"
                )
                
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"❌ [Metrics] {port_name}.failed_at={elapsed_ms:.2f}ms "
                    f"(chunks={chunk_count}, error={type(e).__name__})"
                )
                raise
        
        return wrapper
    return decorator
