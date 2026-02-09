import httpx
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Azure OpenAI no tiene endpoint "list models" para API básica
# Usaremos el endpoint público de OpenAI como referencia
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"

async def fetch_azure_openai_models(api_key: str | None = None) -> List[Dict[str, str]]:
    """
    Obtiene modelos disponibles de OpenAI (compatible con Azure modo básico).
    
    Como Azure básico no expone deployments, retornamos el catálogo
    de modelos más reciente de OpenAI como referencia.
    
    Returns:
        Lista de dicts {id, name} para modelos GPT
    """
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                OPENAI_MODELS_URL,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get("data", [])
            
            # Filtrar: Solo modelos GPT para chat
            gpt_models = [
                m for m in models 
                if m.get("id", "").startswith("gpt-")
                and m.get("object") == "model"
            ]
            
            # Transformar con nombres amigables
            result = []
            for m in gpt_models:
                model_id = m["id"]
                display_name = beautify_azure_model_name(model_id)
                result.append({"id": model_id, "name": display_name})
            
            # Ordenar por relevancia (GPT-4 primero)
            result.sort(key=lambda x: (
                0 if "4o" in x["id"] else
                1 if "4-turbo" in x["id"] else
                2 if "gpt-4" in x["id"] else
                3
            ))
            
            logger.info(f"✅ Cargados {len(result)} modelos Azure/OpenAI desde la API")
            return result
            
    except Exception as e:
        logger.error(f"❌ Error API Azure/OpenAI: {e}")
        return get_azure_fallback_models()


def beautify_azure_model_name(model_id: str) -> str:
    """
    Convierte nombres técnicos de modelos GPT en nombres amigables.
    
    Ejemplo:
        'gpt-4o' → '⭐ GPT-4o (Omni - MEJOR)'
        'gpt-4o-mini' → 'GPT-4o Mini (Rápido + Económico)'
    """
    # Mapeo personalizado para modelos conocidos
    mappings = {
        "gpt-4o": "⭐ GPT-4o (Omni - MEJOR)",
        "gpt-4o-mini": "GPT-4o Mini (Rápido + Económico)",
        "gpt-4-turbo": "GPT-4 Turbo (Alta Capacidad)",
        "gpt-4-turbo-preview": "GPT-4 Turbo Preview",
        "gpt-4": "GPT-4 (Clásico)",
        "gpt-4-0613": "GPT-4 (Junio 2023)",
        "gpt-3.5-turbo": "GPT-3.5 Turbo (Económico)",
        "gpt-35-turbo": "GPT-3.5 Turbo (Económico)",  # Variante Azure
        "gpt-3.5-turbo-16k": "GPT-3.5 Turbo 16K",
    }
    
    # Si tenemos un nombre personalizado, usarlo
    if model_id in mappings:
        return mappings[model_id]
    
    # Embellecimiento automático genérico
    # 'gpt-5-turbo' → 'GPT-5 Turbo'
    beautified = model_id.upper()
    
    # Reemplazar guiones por espacios para legibilidad
    beautified = beautified.replace("-", " ")
    
    # Capitalizar correctamente
    beautified = beautified.replace("GPT ", "GPT-")
    
    return beautified


def get_azure_fallback_models() -> List[Dict[str, str]]:
    """
    Catálogo de respaldo si la API de OpenAI/Azure falla.
    Contiene los modelos más estables y recomendados.
    """
    return [
        {"id": "gpt-4o", "name": "⭐ GPT-4o (Omni - MEJOR)"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Rápido + Económico)"},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo (Alta Capacidad)"},
        {"id": "gpt-4", "name": "GPT-4 (Clásico)"},
        {"id": "gpt-35-turbo", "name": "GPT-3.5 Turbo (Económico)"}
    ]
