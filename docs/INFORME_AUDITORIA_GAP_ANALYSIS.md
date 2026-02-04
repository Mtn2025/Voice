# Informe de Auditoría y Análisis de Brechas (GAP Analysis)

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Comparación estricta entre **Evidencia Visual** (Imágenes) vs **Verificación Funcional** (Simulaciones Realizadas).

Este documento separa los controles que han sido **Simulados y Verificados** de aquellos que **Existen en Código** pero no fueron parte de la simulación exhaustiva original (La "Brecha").

---

## 1. Pestaña Model: Controles Verificados (Simulados)
Estos controles fueron manipulados por el script de prueba y verificados en Base de Datos.

| Control Visual | Ruta Frontend (`dashboard.py` alias) | Ruta Backend (`models.py`) | Schema Pydantic (`ProfileConfigSchema`) | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor LLM** | `llmProvider` | `llm_provider` | `llm_provider: str` | ✅ Verificado |
| **Modelo LLM** | `llmModel` | `llm_model` | `llm_model: str` | ✅ Verificado |
| **Creatividad** | `temperature` | `temperature` | `temperature: float` | ✅ Verificado |
| **Max Tokens** | `max_tokens` (Implicit) | `max_tokens` | `max_tokens: int` | ✅ Verificado |
| **System Prompt** | `systemPrompt` | `system_prompt` | `system_prompt: str` | ✅ Verificado |

---

## 2. Pestaña Model: Controles Existentes NO Verificados (GAP)
Estos controles aparecen en las imágenes y **existen en el código** (confirmado en rutas, BD y Schemas), pero no se incluyeron en el script de simulación `verify_model_transcription_exhaustive.py`.

### A. Estilo de Conversación
| Control Visual | Ruta Frontend | Ruta Backend | Schema Pydantic | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Longitud Respuesta** | `responseLength` | `response_length` | `response_length: str` | ⚠️ Existe (No Sim) |
| **Tono** | `conversationTone` | `conversation_tone` | `conversation_tone: str` | ⚠️ Existe (No Sim) |
| **Formalidad** | `conversationFormality` | `conversation_formality` | `conversation_formality: str` | ⚠️ Existe (No Sim) |
| **Velocidad** | `conversationPacing` | `conversation_pacing` | `conversation_pacing: str` | ⚠️ Existe (No Sim) |

### B. Inteligencia Avanzada
| Control Visual | Ruta Frontend | Ruta Backend | Schema Pydantic | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Ventana Contexto** | `c.contextWindow` | `context_window` | `context_window: int` | ⚠️ Existe (No Sim) |
| **Penalización Frec.** | `c.frequencyPenalty` | `frequency_penalty` | `frequency_penalty: float` | ⚠️ Existe (No Sim) |
| **Penalización Pres.** | `c.presencePenalty` | `presence_penalty` | `presence_penalty: float` | ⚠️ Existe (No Sim) |
| **Estrategia Tools** | `c.toolChoice` | `tool_choice` | `tool_choice: str` | ⚠️ Existe (No Sim) |
| **Variables Din.** | `c.dynamicVars` | `dynamic_vars` | `dynamic_vars: dict` | ⚠️ Existe (No Sim) |

### C. Inicio y Seguridad
| Control Visual | Ruta Frontend | Ruta Backend | Schema Pydantic | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Mensaje Inicial** | `first_message` (Implicit) | `first_message` | `first_message: str` | ⚠️ Existe (No Sim) |
| **Modo Inicio** | `first_message_mode` (Implicit) | `first_message_mode` | `first_message_mode: str` | ⚠️ Existe (No Sim) |
| **Lista Negra** | `blacklist` | `hallucination_blacklist` | `hallucination_blacklist: str` | ⚠️ Existe (No Sim) |

---

## 3. Conclusión Técnica
La "Brecha" es puramente de **cobertura de pruebas**, no de implementación.
*   **Integridad de Código**: 100%. Todos los controles visuales tienen respaldo en `models.py` (BD) y `ProfileConfigSchema` (API).
*   **Cobertura de Pruebas**: ~40% de los controles de la Pestaña Model fueron probados explícitamente.

**Recomendación**: Ejecutar un script de "Cierre de Brecha" que envíe valores aleatorios a todos los campos listados en la Sección 2 para confirmar su persistencia definitiva.
