# Inventario Detallado del Sistema (Post-Auditoría)

> **Fecha:** 27/01/2026
> **Estado:** Validado y Funcional.

---

## 🟢 Sección 1: Modelo Lógico (Cerebro)

| Control Visual | Campo DB / Form | Backend Mapping | Uso Lógico | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor LLM** | `llm_provider` | `AgentConfig.llm_provider` | `ServiceFactory.get_llm_provider()` | ✅ Activo |
| **Modelo LLM** | `llm_model` | `AgentConfig.llm_model` | Pasado a `GroqClient` o `AzureOpenAI` como `model_id`. | ✅ Activo |

---

## 🟢 Sección 2: Estilo de Conversación (UX Abstraction)

Esta sección abstrae instrucciones complejas de Prompting en selectores simples.

| Control Visual | Campo DB | Backend Mapping | Uso Lógico | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Longitud Respuesta** | `response_length` | `AgentConfig.response_length` | `PromptBuilder`: Inyecta "Responde brevemente..." o "Detállate...". | ✅ Activo |
| **Tono Conversación** | `conversation_tone` | `AgentConfig.conversation_tone` | `PromptBuilder`: Inyecta "Sé profesional/amigable/cálido". | ✅ Activo |
| **Nivel Formalidad** | `conversation_formality` | `AgentConfig.conversation_formality` | `PromptBuilder`: Inyecta "Usa 'usted'/'tú'". | ✅ Activo |
| **Velocidad (Pacing)**| `conversation_pacing`| `AgentConfig.conversation_pacing` | `Orchestrator._load_config`: **Sobrescribe** `voice_pacing_ms` y `silence_timeout_ms`. | ✅ Activo |

---

## 🔵 Sección 5: Configuración de Voz (Tab: Voz)

| Control Visual | Campo DB / Form | Backend Mapping | Uso Lógico | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor TTS** | `tts_provider` | `AgentConfig.tts_provider` | `ServiceFactory.get_tts_provider()` | ✅ Activo |
| **Idioma** | `voiceLang` (Frontend) | `AgentConfig.voice_language` | Filtra lista de voces y configura Locale. | ✅ Activo |
| **Género** | `currentGender` (Frontend) | N/A (UI Filter) | Filtra la lista de voces en el navegador. | ✅ Activo |
| **Voz** | `voice_name` | `AgentConfig.voice_name` | ID enviado a Azure/11Labs. | ✅ Activo |
| **Velocidad** | `voice_speed` | `AgentConfig.voice_speed` | Rate SSML (0.5 - 2.0). | ✅ Activo |
| **Interrupción Inteligente**| `segmentation_strategy`| `AgentConfig.segmentation_strategy` | Toggle UI -> 'semantic'/'default' en Backend. | ✅ Activo |
| **Sonido de Fondo** | `background_sound` | `AgentConfig.background_sound` | Mezcla audio en `Orchestrator`. | ✅ Activo |
| **Tono (Pitch)** | `voice_pitch` | `AgentConfig.voice_pitch` | Pitch SSML (-12 a +12 st). | ✅ Activo |
| **Volumen** | `voice_volume` | `AgentConfig.voice_volume` | Volume SSML (0-100). | ✅ Activo |
| **Intensidad Emocional**| `voice_style_degree`| `AgentConfig.voice_style_degree`| Style Degree SSML. Solo visible si hay Style. | ✅ Activo |

---

## 🟢 Sección 3: Parámetros Técnicos

| Control Visual | Campo DB | Backend Mapping | Uso Lógico | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Creatividad** | `temperature` | `AgentConfig.temperature` | Pasado a API LLM (`temperature=0.x`). | ✅ Activo |
| **Max Tokens** | `max_tokens` | `AgentConfig.max_tokens` | Pasado a API LLM (límite de respuesta). | ✅ Activo |
| **System Prompt** | `system_prompt` | `AgentConfig.system_prompt` | Base del Prompt. Se le concatenan los estilos dinámicos. | ✅ Activo |
| **Mensaje Inicial** | `first_message` | `AgentConfig.first_message` | `Orchestrator`: Se envía directo al TTS al iniciar llamada. | ✅ Activo |
| **Modo Inicio** | `first_message_mode`| `AgentConfig.first_message_mode`| `Orchestrator`: Decide si enviar `first_message` o esperar audio. | ✅ Activo |

---

## 🟢 Sección 4: Configuración de Voz (TTS)

| Control Visual | Campo DB | Backend Mapping | Uso Lógico | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor TTS** | `tts_provider` | `AgentConfig.tts_provider` | `ServiceFactory.get_tts_provider()` | ✅ Activo |
| **Voz** | `voice_name` | `AgentConfig.voice_name` | ID de voz Azure (ej. `es-MX-DaliaNeural`). | ✅ Activo |
| **Estilo** | `voice_style` | `AgentConfig.voice_style` | Estilo emocional SSML (ej. `cheerful`). | ✅ Activo |
| **Intensidad Estilo** | `voice_style_degree` | `AgentConfig.voice_style_degree` | Intensidad del estilo (0.01 - 2.0). | ✅ Activo |
| **Velocidad** | `voice_speed` | `AgentConfig.voice_speed` | Rate prosodia SSML (0.5 - 2.0). | ✅ Activo |
| **Pitch** | `voice_pitch` | `AgentConfig.voice_pitch` | Pitch prosodia SSML (semitonos). | ✅ Activo |
| **Volumen** | `voice_volume` | `AgentConfig.voice_volume` | Volumen prosodia SSML. | ✅ Activo |
| **Sonido de Fondo** | `background_sound` | `AgentConfig.background_sound` | Mezcla de audio WAV en `Orchestrator`. | ✅ Activo |

---

## 🟢 Sección 5: Transcriptor (STT) y Entrada

| Control Visual | Campo DB | Backend Mapping | Uso Lógico | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor STT** | `stt_provider` | `AgentConfig.stt_provider` | `ServiceFactory.get_stt_provider()` | ✅ Activo |
| **Idioma** | `stt_language` | `AgentConfig.stt_language` | Configuración de Locale para Azure STT. | ✅ Activo |
| **Interrupt Threshold**| `interruption_threshold` | `AgentConfig.interruption_threshold` | Palabras mínimas para considerar interrupción válida (Browser). | ✅ Activo |
| **Interrup. RMS** | `voice_sensitivity` | `AgentConfig.voice_sensitivity` | Umbral de energía para VAD (Browser). | ✅ Activo |
| **Silence Timeout** | `silence_timeout_ms` | `AgentConfig.silence_timeout_ms` | Tiempo de silencio para cortar turno (Controlado por Pacing). | ✅ Activo |
| **Input Min Chars** | `input_min_characters` | `AgentConfig.input_min_characters` | Filtro de frases demasiado cortas (evita "Ah", "Mm"). | ✅ Activo |
| **Blacklist** | `hallucination_blacklist` | `AgentConfig.hallucination_blacklist` | Filtro de frases repetitivas/alucinaciones de STT. | ✅ Activo |

---

## 🟢 Sección 6: Avanzado y Gestión

| Control Visual | Campo DB | Backend Mapping | Uso Lógico | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Max Duration** | `max_duration` | `AgentConfig.max_duration` | Corte forzoso de llamada. | ✅ Activo |
| **Idle Timeout** | `idle_timeout` | `AgentConfig.idle_timeout` | Tiempo de inactividad antes de preguntar "¿Hola?". | ✅ Activo |
| **Idle Message** | `idle_message` | `AgentConfig.idle_message` | Frase a decir en inactividad. | ✅ Activo |
| **Max Retries** | `inactivity_max_retries` | `AgentConfig.inactivity_max_retries`| Intentos antes de colgar por inactividad. | ✅ Activo |

---

## ❌ Elementos Eliminados (Limpieza Soft)

Estos elementos existen en el esquema de base de datos histórico pero **han sido bloqueados** en la capa de API para evitar confusión y uso accidental.

*   `extraction_model` (Funcionalidad no implementada)
*   `segmentation_strategy` (Configuración interna)
*   `punctuation_boundaries` (Configuración interna)
*   `enable_denoising` (Redundante con proveedor)

