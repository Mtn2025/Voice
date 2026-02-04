# Reporte de Simulación Exhaustiva: Pestañas Model y Transcriptor

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la integridad, persistencia y funcionalidad de los controles de "Cerebro" (LLM) y "Oído" (STT).
**Alcance:** 9 Controles Clave.

## 1. Metodología
*   **Script**: `tests/manual/verify_model_transcription_exhaustive.py`
*   **Fuente de Verdad**: Configuración Persistente en DB (`agent_configs`).
*   **Corrección Aplicada**: Se agregaron columnas `temperature` y `max_tokens` que faltaban en el esquema, habilitando el control de creatividad del LLM.

## 2. Resultados Detallados

### Sección 1: Model (Cerebro)
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor IA** | `llmProvider` | ✅ SÍ | ✅ OK | Persiste correctamente. |
| **Modelo** | `llmModel` | ✅ SÍ | ✅ OK | Persiste correctamente. |
| **Creatividad** | `temperature` | ✅ SÍ | ✅ OK | **Fixed**. Persiste en DB. |
| **Prompt Sistema** | `systemPrompt` | ✅ SÍ | ✅ OK | Persiste correctamente. |

### Sección 2: Transcriptor (Oído)
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor STT** | `sttProvider` | ✅ SÍ | ✅ OK | Persiste correctamente. |
| **Idioma** | `sttLang` | ✅ SÍ | ✅ OK | Persiste correctamente. |
| **Palabras Clave** | `sttKeywords` | ✅ SÍ | ✅ OK | JSON list guardada correctamente. |
| **Formato** | `sttSmartFormatting` | ✅ SÍ | ✅ OK | Boolean guardado correctamente. |
| **Diarización** | `sttDiarization` | ✅ SÍ | ✅ OK | Boolean guardado correctamente. |

## 3. Conclusión
**Prueba Aprobada (100%)**.
Los cerebros (LLM) y oídos (STT) del asistente son totalmente configurables y sus ajustes persisten entre sesiones.
