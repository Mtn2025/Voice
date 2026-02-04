# Reporte de Simulación Exhaustiva: Pestaña Advanced

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la integridad, persistencia y funcionalidad de los controles de la Pestaña "Advanced" (Calidad, Codecs, Safety).
**Alcance:** 7 Controles Clave.

## 1. Metodología
*   **Script**: `tests/manual/verify_advanced_exhaustive.py`
*   **Fuente de Verdad**: `models.py` vs UI.
*   **Método**: Inyección de configuración vía API.

## 2. Resultados Detallados

### Sección 1: Calidad y Latencia
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Paciencia Asistente** | `silenceTimeoutMs` | ✅ SÍ | ✅ OK | Columna `silence_timeout_ms` existe. |
| **Supresión Ruido** | `noiseSuppressionLevel` | ❌ NO | ⚠️ IGNORADO | Falta columna. |
| **Fidelidad Audio** | `audioCodec` | ❌ NO | ⚠️ IGNORADO | Falta columna. |
| **Backchanneling** | `enableBackchannel` | ❌ NO | ⚠️ IGNORADO | Falta columna. |

### Sección 2: Límites de Seguridad
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Duración Máx** | `maxDurationSeconds` | ❌ NO | ⚠️ IGNORADO | Falta columna. |
| **Max Retries** | `maxRetries` | ❌ NO | ⚠️ IGNORADO | Falta columna. |
| **Mensaje Inactividad** | `inactivityMessage` | ❌ NO | ⚠️ IGNORADO | Falta columna. |

## 3. Conclusión
**Prueba Fallida (15% Cobertura)**.
Solo el control de "Paciencia" (Silence Timeout) está soportado por el backend. El resto de las funciones avanzadas (Supresión de Ruido, Codecs, Limits) son visuales y no persisten.

**Acción Requerida**: Crear migración para agregar las 6 columnas faltantes a la tabla `agent_configs`.
