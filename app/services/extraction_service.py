import logging
import json
from app.core.config import settings
from app.core.http_client import http_client

logger = logging.getLogger(__name__)

class ExtractionService:
    """
    Service to handle post-call data extraction using Groq LLM.
    Uses the entire conversation history to extract structured data.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = "llama-3.1-8b-instant" # Fast, cheap, good for extraction
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    async def extract_post_call(self, session_id: str, history: list[dict]) -> dict:
        """
        Analyze conversation history and extract structured data.
        
        Args:
            session_id: The session ID for logging.
            history: List of message dicts {"role": "user/assistant", "content": "..."}

        Returns:
            Dictionary with extracted fields (summary, intent, sentiment, etc.)
        """
        if not history:
            logger.warning(f"⚠️ [EXTRACTION] No history to extract for session {session_id}")
            return {}

        logger.info(f"🔍 [EXTRACTION] Analyzing {len(history)} messages for session {session_id}")

        # Format history for prompt
        dialogue_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in history])

        # Schema Definition (Shared Contract)
        schema = {
            "summary": "Resumen breve de la conversación (1-2 frases).",
            "intent": "agendar_cita | consulta | queja | irrelevante | buzon",
            "sentiment": "positive | neutral | negative",
            "extracted_entities": {
                "name": "Nombre del usuario (si se mencionó)",
                "phone": "Teléfono alternativo (si se mencionó)",
                "email": "Correo (si se mencionó)",
                "appointment_date": "Fecha ISO (si se agendó)"
            },
            "next_action": "follow_up | do_nothing"
        }

        system_prompt = (
            "Eres un analista experto de llamadas. "
            "Tu tarea es extraer información estructurada del siguiente diálogo en formato JSON estricto. "
            "No inventes datos. Si no hay datos, usa null.\n\n"
            f"SCHEMA ESPERADO:\n{json.dumps(schema, indent=2)}"
        )

        try:
            client = http_client.get_client()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"DIÁLOGO:\n{dialogue_text}"}
                ],
                "temperature": 0.1, # Deterministic
                "response_format": {"type": "json_object"}
            }

            response = await client.post(self.api_url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            extracted_data = json.loads(content)
            logger.info(f"✅ [EXTRACTION] Success: {extracted_data.get('intent', 'unknown')}")
            return extracted_data

        except Exception as e:
            logger.error(f"❌ [EXTRACTION] Failed: {e}")
            return {}

# Singleton
extraction_service = ExtractionService()
