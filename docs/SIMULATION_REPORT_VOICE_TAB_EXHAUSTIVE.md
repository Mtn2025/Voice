# Reporte de Simulación Exhaustiva: Pestaña Voz

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la integridad, persistencia y funcionalidad de **TODOS** los controles visibles en la interfaz de usuario ("Voice Tab"), asegurando alineación total entre Frontend y Backend.
**Alcance:** 19 Controles (Azure, ElevenLabs, Humanización, Técnico).

## 1. Metodología
*   **Script**: `tests/manual/verify_voice_exhaustive.py`
*   **Fuente de Verdad**: `store.v2.js` (Frontend Payload).
*   **Método**: Inyección de los *mismos* JSON keys que envía el navegador real.
*   **Corrección Aplicada**: Se agregaron 13 alias faltantes en `app/routers/dashboard.py` (`FIELD_ALIASES`) para resolver el error "Payload Mismatch".

## 2. Resultados Detallados (POST-CORRECCIÓN)

### Sección 1: Configuración Básica
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor TTS** | `voiceProvider` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Idioma** | `voiceLang` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Voz** | `voiceId` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Estilo** | `voiceStyle` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Velocidad** | `voiceSpeed` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Fondo** | `voiceBgSound` | ✅ SÍ | ✅ OK | Mapeado correctamente. |

### Sección 2: Control de Expresión
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Tono (Pitch)** | `voicePitch` | ✅ SÍ | ✅ OK | Alias `voice_pitch` agregado. |
| **Volumen** | `voiceVolume` | ✅ SÍ | ✅ OK | Alias `voice_volume` agregado. |
| **Grado Estilo** | `voiceStyleDegree` | ✅ SÍ | ✅ OK | Alias `voice_style_degree` agregado. |

### Sección 3: Humanización & Técnico
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Muletillas** | `voiceFillerInjection`| ✅ SÍ | ✅ OK | Alias agregado. |
| **Escucha Activa**| `voiceBackchanneling` | ✅ SÍ | ✅ OK | Alias agregado. |
| **Normalización** | `textNormalizationRule`| ✅ SÍ | ✅ OK | Alias agregado. |
| **Latencia** | `ttsLatencyOptimization`| ✅ SÍ | ✅ OK | Alias agregado. |
| **Formato** | `ttsOutputFormat` | ✅ SÍ | ✅ OK | Alias agregado. |

### Sección 4: ElevenLabs Specifics
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Estabilidad** | `voiceStability` | ✅ SÍ | ✅ OK | Alias agregado. |
| **Similitud** | `voiceSimilarityBoost`| ✅ SÍ | ✅ OK | Alias agregado. |
| **Exageración** | `voiceStyleExaggeration`| ✅ SÍ | ✅ OK | Alias agregado. |
| **Boost Speaker** | `voiceSpeakerBoost` | ✅ SÍ | ✅ OK | Alias agregado. |
| **Multilingual** | `voiceMultilingual` | ✅ SÍ | ✅ OK | Alias agregado. |

## 3. Prueba de Llamada Real
*   **Conexión WebSocket**: ✅ Exitosa (`Connected`).
*   **Carga de Configuración**: ✅ El backend aceptó la configuración corregida sin errores.
*   **Audio**: ⚠️ Timeout (Esperado en simulación sin input de audio, pero confirma conexión).

## 4. Conclusión
La **Falla Sistémica de Desalineación de Payloads** ha sido **RESUELTA**.
Se confirma que el 100% de los controles de la Pestaña Voz ahora persisten correctamente en la base de datos y son recibidos por el orquestador. La deuda técnica de "inputs placebo" ha sido eliminada.
