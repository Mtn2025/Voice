"""Use Case: Generate LLM response."""
import logging
from typing import AsyncGenerator
from app.core.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class GenerateResponseUseCase:
    """
    Generates LLM response from user input.
    
    This use case encapsulates conversation management and LLM interaction,
    making it testable without Pipeline or WebSocket dependencies.
    
    Responsibilities:
    - Build system prompt with context injection
    - Manage conversation history
    - Stream LLM tokens
    - Update conversation history with complete response
    
    Dependencies:
    - LLM Provider (any object with get_stream() method)
    - Agent Configuration
    - Optional: CRM/Call context
    
    Example:
        >>> from app.core.di_container import get_llm_provider
        >>> provider = get_llm_provider("groq")
        >>> use_case = GenerateResponseUseCase(provider, config, context={"name": "Juan"})
        >>> history = []
        >>> async for token in use_case.execute("Hola", history):
        ...     print(token, end="")
    """
    
    def __init__(self, llm_provider, config, context: dict = None):
        """
        Initialize use case with LLM provider and configuration.
        
        Args:
            llm_provider: Provider implementing get_stream() method
            config: Agent configuration (AgentConfig model)
            context: Optional context dict (CRM data, call metadata, etc.)
        """
        self.llm = llm_provider
        self.config = config
        self.context = context or {}
    
    async def execute(
        self,
        user_message: str,
        conversation_history: list
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from user message.
        
        Args:
            user_message: Current user input
            conversation_history: List of {role, content} dicts (will be mutated)
        
        Yields:
            str: Response tokens
        
        Side Effects:
            - Appends user message to conversation_history
            - Appends complete assistant response to conversation_history
        
        Example:
            >>> history = []
            >>> response = ""
            >>> async for token in use_case.execute("Hola", history):
            ...     response += token
            >>> len(history)  # 2 (user + assistant)
        """
        # Validate input
        if not user_message or not user_message.strip():
            logger.warning("⚠️ [GenerateResponse UseCase] Empty user message")
            return
        
        # Update history with user message (avoid duplicates)
        if not conversation_history or conversation_history[-1].get("content") != user_message:
            conversation_history.append({"role": "user", "content": user_message})
            logger.debug(f"📝 [GenerateResponse UseCase] Added user message to history (len={len(conversation_history)})")
        
        # Build system prompt with context injection
        try:
            system_prompt = PromptBuilder.build_system_prompt(self.config, self.context)
            logger.debug(f"🔧 [GenerateResponse UseCase] System prompt built ({len(system_prompt)} chars)")
        except Exception as e:
            logger.error(f"❌ [GenerateResponse UseCase] Failed to build system prompt: {e}")
            # Fallback to simple prompt
            system_prompt = getattr(self.config, 'system_prompt', "You are a helpful assistant.")
        
        # Get generation parameters
        temperature = float(getattr(self.config, 'temperature', 0.7))
        max_tokens = int(getattr(self.config, 'max_tokens', 150))
        
        logger.info(
            f"🤖 [GenerateResponse UseCase] Generating response "
            f"(user_msg_len={len(user_message)}, temp={temperature}, max_tokens={max_tokens})"
        )
        
        # Stream from LLM provider
        full_response = ""
        token_count = 0
        
        try:
            async for token in self.llm.get_stream(
                messages=conversation_history,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                full_response += token
                token_count += 1
                yield token
        
        except Exception as e:
            logger.error(f"❌ [GenerateResponse UseCase] LLM streaming error: {e}")
            raise
        
        # Update history with complete response
        if full_response.strip():
            conversation_history.append({"role": "assistant", "content": full_response})
            logger.info(
                f"✅ [GenerateResponse UseCase] Response complete "
                f"({len(full_response)} chars, {token_count} tokens, history_len={len(conversation_history)})"
            )
        else:
            logger.warning("⚠️ [GenerateResponse UseCase] Empty response from LLM")
    
    async def execute_non_streaming(
        self,
        user_message: str,
        conversation_history: list
    ) -> str:
        """
        Generate non-streaming response (collects all tokens).
        
        Convenience method for use cases that don't need streaming.
        
        Args:
            user_message: Current user input
            conversation_history: List of {role, content} dicts
        
        Returns:
            str: Complete response
        """
        full_response = ""
        
        async for token in self.execute(user_message, conversation_history):
            full_response += token
        
        return full_response
