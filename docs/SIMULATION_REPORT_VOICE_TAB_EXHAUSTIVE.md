# Reporte de Simulación Exhaustiva: Pestaña Voz

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la integridad y persistencia de **TODOS** los controles visibles en la interfaz de usuario ("Voice Tab") con rigor arquitectónico.
**Alcance:** 19 Controles (Azure, ElevanLabs, Humanización, Técnico).

## 1. Metodología
*   **Script**: `tests/manual/verify_voice_exhaustive.py`
*   **Fuente de Verdad**: `app/static/js/dashboard/store.v2.js` (Frontend Payload).
*   **Método**: Inyección de los *mismos* JSON keys que envía el navegador real.
*   **Verificación**: Validación de `updated > 0` en respuesta del backend.

## 2. Resultados Detallados (CRÍTICO)

### Sección 1: Configuración Básica
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Proveedor TTS** | `voiceProvider` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Idioma** | `voiceLang` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Voz** | `voiceId` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Estilo** | `voiceStyle` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Velocidad** | `voiceSpeed` | ✅ SÍ | ✅ OK | Mapeado correctamente. |
| **Fondo** | `voiceBgSound` | ✅ SÍ | ✅ OK | Mapeado correctamente. |

### Sección 2: Control de Expresión (FALLA SISTÉMICA)
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Tono (Pitch)** | `voicePitch` | ❌ NO | 🚨 ERROR | Backend ignora la key (Falta Alias). |
| **Volumen** | `voiceVolume` | ❌ NO | 🚨 ERROR | Backend ignora la key (Falta Alias). |
| **Grado Estilo** | `voiceStyleDegree` | ❌ NO | 🚨 ERROR | Backend ignora la key (Falta Alias). |

### Sección 3: Humanización & Técnico (FALLA SISTÉMICA)
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Muletillas** | `voiceFillerInjection`| ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Escucha Activa**| `voiceBackchanneling` | ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Normalización** | `textNormalizationRule`| ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Latencia** | `ttsLatencyOptimization`| ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Formato** | `ttsOutputFormat` | ❌ NO | 🚨 ERROR | Backend ignora la key. |

### Sección 4: ElevenLabs Specifics (FALLA SISTÉMICA)
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Estabilidad** | `voiceStability` | ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Similitud** | `voiceSimilarityBoost`| ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Exageración** | `voiceStyleExaggeration`| ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Boost Speaker** | `voiceSpeakerBoost` | ❌ NO | 🚨 ERROR | Backend ignora la key. |
| **Multilingual** | `voiceMultilingual` | ❌ NO | 🚨 ERROR | Backend ignora la key. |

## 3. Diagnóstico de Código
Existe una **Desalineación de Payloads (Payload Mismatch)** masiva.
*   **Frontend**: Envía keys en formato `camelCase` (ej. `voicePitch`).
*   **Backend (`dashboard.py`)**: Carece de entradas en `FIELD_ALIASES` para mapear estas keys a `snake_case` (`voice_pitch`).
*   **Resultado**: El endpoint `/api/config/update-json` filtra estas keys como "desconocidas" y **NO** actualiza la base de datos.
*   **Impacto en Producción**: 13/19 controles de voz son "placebo". El usuario cree que guarda la configuración, pero el sistema usa los valores por defecto.

## 4. Conclusión
La pestaña "Voz" presenta **Deuda Técnica Crítica**. El 68% de los controles visuales no tienen efecto en el backend. Se requiere una refactorización urgente de `FIELD_ALIASES` en el backend para alinear el contrato de API.
