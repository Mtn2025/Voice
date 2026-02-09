import httpx
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

async def fetch_groq_models(api_key: str) -> List[Dict[str, str]]:
    """
    Obtiene los modelos disponibles desde la API de Groq.
    
    Returns:
        Lista de dicts {id, name} para modelos compatibles con chat
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GROQ_MODELS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get("data", [])
            
            # Filtrar: Solo modelos con capacidad de chat
            chat_models = [
                m for m in models 
                if m.get("object") == "model" 
                and "id" in m
            ]
            
            # Transformar a nuestro formato con nombres amigables
            result = []
            for m in chat_models:
                model_id = m["id"]
                display_name = beautify_model_name(model_id)
                result.append({"id": model_id, "name": display_name})
            
            logger.info(f"✅ Cargados {len(result)} modelos Groq desde la API")
            return result
            
    except Exception as e:
        logger.error(f"❌ Error API Groq: {e}")
        return get_groq_fallback_models()


def beautify_model_name(model_id: str) -> str:
    """
    Convierte nombres técnicos en nombres amigables para el usuario.
    
    Ejemplo:
        'llama-3.3-70b-versatile' → '⭐ Llama 3.3 70B Versatile (Recomendado)'
        'gemma-2-9b-it' → 'Gemma 2 9B IT'
    """
    # Mapeo personalizado para modelos conocidos (nombres curados)
    mappings = {
        "llama-3.3-70b-versatile": "⭐ Llama 3.3 70B Versatile (Recomendado)",
        "llama-3.3-70b-specdec": "Llama 3.3 70B SpecDec (Ultra Rápido)",
        "llama-3.1-70b-versatile": "Llama 3.1 70B Versatile",
        "llama-3.1-8b-instant": "Llama 3.1 8B Instant (Económico)",
        "llama-3.2-90b-vision-preview": "Llama 3.2 90B Vision (Preview)",
        "llama-3.2-11b-vision-preview": "Llama 3.2 11B Vision (Preview)",
        "llama-3.2-3b-preview": "Llama 3.2 3B (Preview)",
        "llama-3.2-1b-preview": "Llama 3.2 1B (Preview)",
        "gemma-2-9b-it": "Gemma 2 9B IT",
        "gemma2-9b-it": "Gemma 2 9B IT",
        "mixtral-8x7b-32768": "Mixtral 8x7B",
        "llama-guard-3-8b": "Llama Guard 3 8B (Moderación)",
    }
    
    # Si tenemos un nombre personalizado, usarlo
    if model_id in mappings:
        return mappings[model_id]
    
    # Embellecimiento automático genérico para modelos nuevos
    # Convertir 'llama-4-200b-instant' → 'Llama 4 200B Instant'
    beautified = model_id.replace("-", " ").title()
    
    # Mejorar casos específicos comunes
    beautified = beautified.replace("Llm", "LLM")
    beautified = beautified.replace("Gpt", "GPT")
    beautified = beautified.replace("Api", "API")
    beautified = beautified.replace(" It", " IT")
    beautified = beautified.replace("Ai", "AI")
    
    return beautified


def get_groq_fallback_models() -> List[Dict[str, str]]:
    """
    Catálogo de respaldo si la API de Groq falla.
    Contiene los modelos más estables y recomendados.
    """
    return [
        {"id": "llama-3.3-70b-versatile", "name": "⭐ Llama 3.3 70B Versatile (Recomendado)"},
        {"id": "llama-3.3-70b-specdec", "name": "Llama 3.3 70B SpecDec (Ultra Rápido)"},
        {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B Versatile"},
        {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant (Económico)"},
        {"id": "gemma-2-9b-it", "name": "Gemma 2 9B IT"},
        {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
    ]
