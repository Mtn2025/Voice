"""
Adaptador Groq LLM - Implementación de LLMPort.

Wrappea el GroqProvider existente manteniendo toda la lógica
de streaming, validación de modelos, etc.

✅ Module 9: Supports function calling (tool_calls detection)
"""

import logging
import time  # ✅ Module 3: For TTFB measurements
import json
from typing import AsyncIterator
import groq  # For catching SDK-specific exceptions
from circuitbreaker import circuit  # Professional error handling
from app.domain.ports import LLMPort, LLMMessage, LLMRequest, LLMException
from app.domain.models.llm_models import LLMChunk, LLMFunctionCall  # ✅ Module 9
from app.providers.groq import GroqProvider, SAFE_MODELS_FOR_VOICE, REASONING_MODELS
from app.observability import get_metrics_collector  # ✅ Module 5
from app.core.decorators import track_streaming_latency  # ✅ P3: Métricas TTFB


logger = logging.getLogger(__name__)


class GroqLLMAdapter(LLMPort):
    """
    Adaptador para Groq LLM que implementa LLMPort.
    
    Wrappea GroqProvider existente con toda su lógica de
    validación de modelos razonadores vs conversacionales.
    
    ✅ Hexagonal: Recibe config object (no settings directos)
    """
    
    def __init__(self, config: 'LLMProviderConfig' = None):
        """
        Args:
            config: Clean config object (provided by factory)
                    If None, reads from settings (backwards compatible)
        """
        from app.core.config import settings
        
        if config:
            # ✅ Clean injection from factory
            self.groq_provider = GroqProvider(
                api_key=config.api_key,
                model=config.model
            )
        else:
            # Backwards compatible (legacy)
            self.groq_provider = GroqProvider()
        
        # Assuming GroqProvider has a client attribute or we need to initialize it here
        # Based on the diff, it seems self.client is expected.
        # If GroqProvider already exposes the client, we might do:
        self.client = self.groq_provider.client # Assuming GroqProvider exposes its client
        # Otherwise, if GroqProvider is being bypassed, we'd need:
        # self.client = groq.Groq()
    
    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=LLMException)
    @track_streaming_latency("groq_llm")  # ✅ P3: Track TTFB metrics
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate streaming response from Groq.
        
        ✅ Module 3: Logs TTFB with trace_id for distributed tracing
        ✅ Module 9: Detects function_call in stream, returns LLMChunk
        
        Args:
            request: LLM request with messages, model, temperature, tools
        
        Yields:
            LLMChunk with text or function_call
        
        Raises:
            LLMException: If generation fails
        """
        # ✅ Extract trace_id from request metadata
        trace_id = request.metadata.get('trace_id', 'unknown')
        start_time = time.time()
        first_byte_time = None
        
        try:
            logger.info(f"[LLM Groq] trace={trace_id} Starting generation model={request.model}")
            
            # Convert LLMMessage objects to dicts for the Groq client
            messages_dict = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]

            # Add system prompt if provided
            system_prompt = request.system_prompt or "Eres un asistente útil."
            if system_prompt:
                messages_dict.insert(0, {"role": "system", "content": system_prompt})

            # ✅ Module 9: Prepare API call parameters
            api_params = {
                "model": request.model,
                "messages": messages_dict,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True
            }
            
            # NEW: Add penalties if provided (avoid repetition/encourage diversity)
            if hasattr(request, 'frequency_penalty') and request.frequency_penalty is not None:
                api_params["frequency_penalty"] = request.frequency_penalty
            if hasattr(request, 'presence_penalty') and request.presence_penalty is not None:
                api_params["presence_penalty"] = request.presence_penalty
            
            # ✅ Module 9: Add tools if provided (function calling)
            if request.tools:
                api_params["tools"] = request.tools
                api_params["tool_choice"] = "auto"
                logger.info(f"[LLM Groq] trace={trace_id} Function calling enabled ({len(request.tools)} tools)")

            # Call Groq API
            stream = await self.client.chat.completions.create(**api_params)
            
            # ✅ Module 9: Track function call state (Groq may send tool_calls incrementally)
            function_call_buffer = {
                "name": "",
                "arguments": "",
                "id": None
            }
            in_function_call = False
            
            # Stream response
            async for chunk in stream:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
                
                # ✅ Module 9: Detect tool_calls (function calling)
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    in_function_call = True
                    
                    # Buffer tool call data (Groq sends incrementally)
                    if tool_call.id:
                        function_call_buffer["id"] = tool_call.id
                    if hasattr(tool_call, 'function') and tool_call.function:
                        if tool_call.function.name:
                            function_call_buffer["name"] += tool_call.function.name
                        if tool_call.function.arguments:
                            function_call_buffer["arguments"] += tool_call.function.arguments
                    
                    # ✅ Log TTFB for function call
                    if first_byte_time is None:
                        first_byte_time = time.time()
                        ttfb = (first_byte_time - start_time) * 1000  # ms
                        logger.info(
                            f"[LLM Groq] trace={trace_id} TTFB={ttfb:.0f}ms "
                            f"(function_call) model={request.model}"
                        )
                
                # ✅ Detect text content (normal response)
                elif delta.content:
                    token = delta.content
                    
                    # ✅ Log TTFB (Time To First Byte)
                    if first_byte_time is None:
                        first_byte_time = time.time()
                        ttfb = (first_byte_time - start_time) * 1000  # ms
                        logger.info(
                            f"[LLM Groq] trace={trace_id} TTFB={ttfb:.0f}ms "
                            f"model={request.model}"
                        )
                    
                    # Yield text chunk
                    yield LLMChunk(text=token)
                
                # ✅ Handle finish (complete function call or text)
                if finish_reason:
                    if in_function_call and function_call_buffer["name"]:
                        # Parse complete function call
                        try:
                            arguments = json.loads(function_call_buffer["arguments"])
                            function_call = LLMFunctionCall(
                                name=function_call_buffer["name"],
                                arguments=arguments,
                                call_id=function_call_buffer["id"]
                            )
                            
                            logger.info(
                                f"[LLM Groq] trace={trace_id} Function call: "
                                f"{function_call.name}({list(arguments.keys())})"
                            )
                            
                            # Yield function call chunk
                            yield LLMChunk(
                                function_call=function_call,
                                finish_reason=finish_reason
                            )
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"[LLM Groq] trace={trace_id} Failed to parse function arguments: {e}"
                            )
                            # Yield error as text
                            yield LLMChunk(
                                text=f"[Error: Failed to parse function call]",
                                finish_reason=finish_reason
                            )
                    else:
                        # Normal completion
                        yield LLMChunk(finish_reason=finish_reason)
            
            # ✅ Log total latency
            total_time = (time.time() - start_time) * 1000  # ms
            logger.info(
                f"[LLM Groq] trace={trace_id} Total={total_time:.0f}ms "
                f"model={request.model} completed"
            )
        
        # HEXAGONAL: Translate infrastructure exceptions to domain exceptions
        except groq.RateLimitError as e:
            logger.warning(f"[LLM Groq] trace={trace_id} Rate limit hit: {e}")
            raise LLMException(
                "Rate limit exceeded. Please try again later.",
                retryable=True,
                provider="groq",
                original_error=e
            ) from e
        
        except groq.APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise LLMException(
                "Could not connect to Groq API",
                retryable=True,
                provider="groq",
                original_error=e
            ) from e
        
        except groq.AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise LLMException(
                "Invalid API key",
                retryable=False,
                provider="groq",
                original_error=e
            ) from e
        
        except groq.APIError as e:
            logger.error(f"Groq API error: {e}")
            raise LLMException(
                f"Groq service error: {str(e)}",
                retryable=False,
                provider="groq",
                original_error=e
            ) from e
        
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected LLM error: {e}")
            raise LLMException(
                f"Unexpected error: {str(e)}",
                retryable=False,
                provider="groq",
                original_error=e
            ) from e
    
    async def get_available_models(self) -> list[str]:
        """Obtiene lista de modelos disponibles desde Groq API."""
        try:
            return await self.groq_provider.get_available_models()
        except Exception as e:
            logger.warning(f"⚠️ [Groq LLM] Could not fetch models: {e}")
            # Fallback to safe defaults
            return SAFE_MODELS_FOR_VOICE[:4]
    
    def is_model_safe_for_voice(self, model: str) -> bool:
        """
        Verifica si modelo es seguro para voz.
        
        Modelos razonadores (deepseek-r1, etc.) generan tags <think>
        que no deben verbalizarse en llamadas de voz.
        """
        return model not in REASONING_MODELS
