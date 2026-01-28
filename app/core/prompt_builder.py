from typing import Any
import logging

class PromptBuilder:
    """
    Constructs the dynamic System Prompt based on AgentConfig options.
    Translates UI enums (tone, formality, length) into natural language instructions.
    """

    @staticmethod
    def build_system_prompt(config: Any, context: dict = None) -> str:
        """
        Combines base system prompt with dynamic style instructions AND context variables.
        """
        base_prompt = getattr(config, 'system_prompt', '') or "Eres un asistente útil."
        
        # 1. Parsing Configuration
        length = getattr(config, 'response_length', 'short')
        tone = getattr(config, 'conversation_tone', 'warm')
        formality = getattr(config, 'conversation_formality', 'semi_formal')
        # pacing = getattr(config, 'conversation_pacing', 'moderate') # pacing is strictly related to TTS speed usually, or prompt brevity
        
        # 2. Instruction Maps
        length_instructions = {
            "very_short": "Responde de forma extremadamente concisa (máximo 10 palabras).",
            "short": "Mantén las respuestas cortas y directas (1-2 frases).",
            "medium": "Da explicaciones equilibradas, ni muy cortas ni muy largas.",
            "long": "Desarróllate libremente, da respuestas completas.",
            "detailed": "Provee tanto detalle como sea posible, sé exhaustivo."
        }
        
        tone_instructions = {
            "professional": "Mantén un tono estrictamente profesional, objetivo y corporativo.",
            "friendly": "Sé amigable y cercano, como un colega.",
            "warm": "Usa un tono cálido, empático y acogedor, haz sentir bien al usuario.",
            "enthusiastic": "Muestra energía y entusiasmo, sé motivador.",
            "neutral": "Sé neutral y desapegado, solo hechos.",
            "empathetic": "Muestra profunda comprensión y cuidado por las emociones."
        }
        
        formality_instructions = {
            "very_formal": "Usa un lenguaje muy formal y respetuoso (trata de 'usted', vocabulario elevado).",
            "formal": "Trata de 'usted' y mantén la etiqueta.",
            "semi_formal": "Equilibrado: respetuoso pero accesible (puedes usar 'usted' o 'tú' según contexto).",
            "casual": "Trata de 'tú', sé relajado y natural.",
            "very_casual": "Usa jerga coloquial, sé muy informal, como un amigo."
        }
        
        # 3. Construct Overrides
        style_block = []
        if length in length_instructions:
            style_block.append(f"- Longitud: {length_instructions[length]}")
        
        if tone in tone_instructions:
            style_block.append(f"- Tono: {tone_instructions[tone]}")
            
        if formality in formality_instructions:
            style_block.append(f"- Formalidad: {formality_instructions[formality]}")
            
        # 4. Inject into Prompt
        # We assume the base prompt has <style> tags or we append a [DYNAMIC STYLE] section.
        # Robust approach: Append at the end (Recency bias helps instruction following).
        
        dynamic_instructions = "\n".join(style_block)
        
        final_prompt = f"""{base_prompt}

<dynamic_style_overrides>
{dynamic_instructions}
</dynamic_style_overrides>
</dynamic_style_overrides>
"""
        # 5. Inject Context Variables (Campaign Data)
        if context:
            try:
                # Format as structured block
                context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
                final_prompt += f"""
<context_data>
{context_str}
</context_data>
"""
            except Exception as e:
                logging.warning(f"Error injecting context: {e}")

        return final_prompt
        return final_prompt
