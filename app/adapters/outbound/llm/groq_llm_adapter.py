"""
Adaptador Groq LLM - Implementación de LLMPort.

Implementa lógica de streaming, validación de modelos y function calling
directamente sobre el cliente oficial de Groq.
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import groq
from circuitbreaker import circuit
from groq import AsyncGroq

from app.core.config import settings
from app.core.decorators import track_streaming_latency
from app.domain.models.llm_models import LLMChunk, LLMFunctionCall
from app.domain.ports import LLMException, LLMPort, LLMRequest

logger = logging.getLogger(__name__)

# Model Safety Constants
# SAFE_MODELS: Do NOT generate <think> tags, suitable for voice
SAFE_MODELS_FOR_VOICE = [
    "llama-3.3-70b-versatile",
    "llama-3.3-70b-specdec",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-4-maverick-17b-128e",
    "gemma-2-9b-it",
    "gemma-7b",
    "mixtral-8x7b-32768"
]

# REASONING MODELS: Generate <think> tags, NOT recommended for voice
REASONING_MODELS = [
    "deepseek-r1-distill-llama-70b",
    "deepseek-chat",
    "deepseek-reasoner"
]


class GroqLLMAdapter(LLMPort):
    """
    Adaptador para Groq LLM que implementa LLMPort.

    Gestiona cliente Groq, streaming y validación de modelos seguros.
    """

    def __init__(self, config: Any | None = None):
        """
        Args:
            config: Clean config object or None.
        """
        api_key = config.api_key if config else settings.GROQ_API_KEY
        self.default_model = config.model if config else settings.GROQ_MODEL

        if not api_key:
             logger.warning("⚠️ Groq API Key missing. Adapter may fail.")

        self.client = AsyncGroq(api_key=api_key)

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=LLMException)
    @track_streaming_latency("groq_llm")
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """
        Generate streaming response from Groq.

        Logs TTFB with trace_id for distributed tracing.
        Detects function_call in stream, returns LLMChunk.
        """
        trace_id = request.metadata.get('trace_id', 'unknown')
        start_time = time.time()
        first_byte_time = None

        try:
            logger.info(f"[LLM Groq] trace={trace_id} Starting generation model={request.model}")

            # Model Validation: Warn if reasoning model used for voice
            if request.model in REASONING_MODELS:
                logger.warning(
                    f"⚠️ REASONING MODEL ALERT: '{request.model}' generates <think> tags! "
                    f"This may cause verbalized thinking in voice output. "
                    f"Recommended safe models: {', '.join(SAFE_MODELS_FOR_VOICE[:3])}"
                )

            messages_dict = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]

            system_prompt = request.system_prompt or "Eres un asistente útil."
            if system_prompt:
                messages_dict.insert(0, {"role": "system", "content": system_prompt})

            api_params = {
                "model": request.model or self.default_model,
                "messages": messages_dict,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True,
                "stop": ["User:", "System:", "\n\nUser", "\n\nSystem"]
            }

            if hasattr(request, 'frequency_penalty') and request.frequency_penalty is not None:
                api_params["frequency_penalty"] = request.frequency_penalty
            if hasattr(request, 'presence_penalty') and request.presence_penalty is not None:
                api_params["presence_penalty"] = request.presence_penalty

            if request.tools:
                api_params["tools"] = request.tools
                api_params["tool_choice"] = "auto"
                logger.info(f"[LLM Groq] trace={trace_id} Function calling enabled ({len(request.tools)} tools)")

            stream = await self.client.chat.completions.create(**api_params)

            function_call_buffer = {
                "name": "",
                "arguments": "",
                "id": None
            }
            in_function_call = False

            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason

                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    in_function_call = True

                    if tool_call.id:
                        function_call_buffer["id"] = tool_call.id
                    if hasattr(tool_call, 'function') and tool_call.function:
                        if tool_call.function.name:
                            function_call_buffer["name"] += tool_call.function.name
                        if tool_call.function.arguments:
                            function_call_buffer["arguments"] += tool_call.function.arguments

                    if first_byte_time is None:
                        first_byte_time = time.time()
                        ttfb = (first_byte_time - start_time) * 1000
                        logger.info(
                            f"[LLM Groq] trace={trace_id} TTFB={ttfb:.0f}ms "
                            f"(function_call) model={request.model}"
                        )

                elif delta.content:
                    token = delta.content

                    if first_byte_time is None:
                        first_byte_time = time.time()
                        ttfb = (first_byte_time - start_time) * 1000
                        logger.info(
                            f"[LLM Groq] trace={trace_id} TTFB={ttfb:.0f}ms "
                            f"model={request.model}"
                        )

                    yield LLMChunk(text=token)

                if finish_reason:
                    if in_function_call and function_call_buffer["name"]:
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

                            yield LLMChunk(
                                function_call=function_call,
                                finish_reason=finish_reason
                            )
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"[LLM Groq] trace={trace_id} Failed to parse function arguments: {e}"
                            )
                            yield LLMChunk(
                                text="[Error: Failed to parse function call]",
                                finish_reason=finish_reason
                            )
                    else:
                        yield LLMChunk(finish_reason=finish_reason)

            total_time = (time.time() - start_time) * 1000
            logger.info(
                f"[LLM Groq] trace={trace_id} Total={total_time:.0f}ms "
                f"model={request.model} completed"
            )

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
                f"Groq service error: {e!s}",
                retryable=False,
                provider="groq",
                original_error=e
            ) from e

        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}")
            raise LLMException(
                f"Unexpected error: {e!s}",
                retryable=False,
                provider="groq",
                original_error=e
            ) from e

    async def get_available_models(self) -> list[str]:
        """Obtiene lista de modelos disponibles desde Groq API."""
        try:
            # Dynamic Fetch from Groq API
            models = await self.client.models.list()
            # Filter out Whisper/Audio models
            return [m.id for m in models.data if "whisper" not in m.id]
        except Exception as e:
            logger.warning(f"⚠️ [Groq LLM] Could not fetch models: {e}")
            # Return safe default
            return SAFE_MODELS_FOR_VOICE[:4]

    def is_model_safe_for_voice(self, model: str) -> bool:
        """
        Verifica si modelo es seguro para voz.
        """
        return model not in REASONING_MODELS
