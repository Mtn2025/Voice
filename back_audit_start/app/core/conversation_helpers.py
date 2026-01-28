"""
Conversation and response management helper functions for VoiceOrchestrator.

Extracted from orchestrator.py to improve code organization and maintainability.
Contains hallucination detection, interruption policy, and smart resume logic.
"""
import logging
import re


def is_hallucination(text: str, config) -> bool:
    """
    Detect if LLM response contains hallucinated/inappropriate content.

    Args:
        text: LLM response text to check
        config: Agent configuration with hallucination patterns

    Returns:
        True if hallucination detected, False otherwise
    """
    if not text:
        return False

    text_lower = text.lower()

    # Check hallucination patterns from config
    hallucination_patterns = getattr(config, 'hallucination_patterns', [
        "i don't have",
        "i cannot",
        "i can't",
        "i'm not able",
        "no tengo acceso",
        "no puedo acceder",
        "lo siento, no puedo"
    ])

    for pattern in hallucination_patterns:
        if pattern.lower() in text_lower:
            logging.warning(f"🚨 Hallucination detected: '{pattern}' in response")
            return True

    return False


def check_interruption_policy(config, conversation_history: list, is_bot_speaking: bool) -> bool:
    """
    Determine if user interruption should be allowed based on policy.

    Args:
        config: Agent configuration
        conversation_history: Current conversation history
        is_bot_speaking: Whether bot is currently speaking

    Returns:
        True if interruption should be allowed, False otherwise
    """
    interruption_mode = getattr(config, 'interruption_mode', 'anytime')

    if interruption_mode == 'disabled':
        return False
    if interruption_mode == 'anytime':
        return True
    if interruption_mode == 'after_first_response':
        # Allow interruption only after bot has spoken at least once
        bot_responses = [msg for msg in conversation_history if msg.get('role') == 'assistant']
        return len(bot_responses) > 0
    # Unknown mode, default to anytime
    return True


def handle_smart_resume(
    interrupted_text: str,
    new_user_input: str,
    conversation_history: list,
    config
) -> str | None:
    """
    Generate smart resume intro when user interrupts bot mid-sentence.

    Args:
        interrupted_text: Text that was being spoken when interrupted
        new_user_input: What user said to interrupt
        conversation_history: Current conversation history
        config: Agent configuration

    Returns:
        Smart resume intro text, or None if not applicable
    """
    smart_resume_enabled = getattr(config, 'smart_resume_enabled', True)

    if not smart_resume_enabled:
        return None

    if not interrupted_text or len(interrupted_text) < 20:
        # Interruption was too early, don't resume
        return None

    # Check if interruption seems related to current topic
    if _is_topic_change(interrupted_text, new_user_input):
        # User changed topic, don't resume
        return None

    # Generate smart resume
    # Extract last completed thought from interrupted text
    sentences = re.split(r'[.!?]+', interrupted_text)
    last_sentence = sentences[-2] if len(sentences) > 1 else ""

    if last_sentence and len(last_sentence) > 10:
        resume_intro = f"Como te decía, {last_sentence.strip()}."
        return resume_intro

    return None


def _is_topic_change(previous_text: str, new_input: str) -> bool:
    """
    Heuristic to detect if user changed conversation topic.

    Args:
        previous_text: What bot was saying
        new_input: What user said

    Returns:
        True if likely topic change, False otherwise
    """
    # Simple heuristic: check for common topic-change phrases
    topic_change_indicators = [
        "pero",
        "cambiando de tema",
        "hablando de otra cosa",
        "por cierto",
        "espera",
        "mejor",
        "no me interesa"
    ]

    new_input_lower = new_input.lower()

    return any(indicator in new_input_lower for indicator in topic_change_indicators)


def extract_control_token(text: str) -> str | None:
    """
    Extract control tokens from LLM response ([END_CALL], [TRANSFER], [DTMF]).

    Args:
        text: LLM response text

    Returns:
        Control token if found, None otherwise
    """
    control_tokens = ['[END_CALL]', '[TRANSFER]', '[DTMF]']

    for token in control_tokens:
        if token in text:
            return token

    return None
