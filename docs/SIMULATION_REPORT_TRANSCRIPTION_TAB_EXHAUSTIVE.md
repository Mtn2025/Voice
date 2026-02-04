# Reporte de Simulación Exhaustiva: Pestaña Transcriptor

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la integridad, persistencia y funcionalidad de **TODOS** los controles visibles en la interfaz de usuario ("Transcriptor Tab").
**Alcance:** 12 Controles (Deepgram/Azure, Interrupciones, Inteligencia).

## 1. Metodología
*   **Script**: `tests/manual/verify_transcription_exhaustive.py`
*   **Fuente de Verdad**: Imágenes de UI + `store.v2.js` (Frontend Payload).
*   **Método**: Inyección de los mismos JSON keys que envía el navegador real.
*   **Verificación**: Validación de `updated > 0` en respuesta del backend.

## 2. Resultados Detallados

### Sección 1: Configuración Principal & Idioma
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor STT** | `sttProvider` | ✅ SÍ | ✅ OK | Persistido correctamente. |
| **Idioma** | `sttLang` | ✅ SÍ | ✅ OK | Persistido correctamente. |
| **Keywords Boost** | `sttKeywords` | ✅ SÍ | ✅ OK | JSON String guardado/parseado OK. |

### Sección 2: Control de Interrupciones
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Umbral Palabras** | `interruptWords`| ✅ SÍ | ✅ OK | Integer persistido. |
| **Blacklist** | `blacklist` | ✅ SÍ | ✅ OK | Alias `hallucination_blacklist`. |
| **Endpointing** | `silence` | ✅ SÍ | ✅ OK | Alias `silence_timeout_ms`. |
| **Sensibilidad VAD**| `interruptRMS` | ✅ SÍ | ✅ OK | Persistido (Generic/Silero). |

### Sección 3: Inteligencia de Transcripción
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Puntuación Auto** | `sttPunctuation`| ✅ SÍ | ✅ OK | Boolean persistido. |
| **Smart Formatting**| `sttSmartFormatting`| ✅ SÍ | ✅ OK | Boolean persistido. |
| **Filtro Groserías**| `sttProfanityFilter`| ✅ SÍ | ✅ OK | Boolean persistido. |
| **Diarización (A/B)**| `sttDiarization` | ✅ SÍ | ✅ OK | Boolean persistido. |
| **Multi-Lenguaje** | `sttMultilingual` | ✅ SÍ | ✅ OK | Boolean persistido. |

## 3. Prueba de Llamada Real
*   **Conexión WebSocket**: ✅ Exitosa (`Connected`).
*   **Carga de Configuración**: ✅ El orquestador inicializó los servicios de STT (Deepgram/Azure) con los parámetros inyectados sin reportar errores de esquema.

## 4. Conclusión
**Prueba Aprobada (100%)**.
A diferencia de la Pestaña Voz, la Pestaña Transcriptor **NO presenta desalineación de payloads**. Todos los controles visuales tienen su alias correspondiente en `dashboard.py` y persisten correctamente en la base de datos `AgentConfig`.
