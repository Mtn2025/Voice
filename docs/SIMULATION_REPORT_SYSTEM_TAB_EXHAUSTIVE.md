# Reporte de Simulación Exhaustiva: Pestaña System

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la integridad, persistencia y funcionalidad de los controles de la Pestaña "Sistema & Gobierno" (Phase VIII).
**Alcance:** 5 Controles (Seguridad y Privacidad).

## 1. Metodología
*   **Script**: `tests/manual/verify_system_exhaustive.py`
*   **Fuente de Verdad**: `models.py` vs UI.
*   **Método**: Inyección de configuración vía API para parámetros de gobernanza.

## 2. Resultados Detallados

### Sección 1: Límites de Seguridad (Safety) - FALLO
| Control (UI) | Key (Frontend) | Guardado | Estado | Diagnóstico |
| :--- | :--- | :--- | :--- | :--- |
| **Concurrency Limit** | `concurrencyLimit` | ❌ NO | ⚠️ IGNORADO | Falta columna `concurrency_limit` en DB. |
| **Daily Spend Limit** | `spendLimitDaily` | ❌ NO | ⚠️ IGNORADO | Falta columna `spend_limit_daily` en DB. |

### Sección 2: Entorno & Privacidad - FALLO
| Control (UI) | Key (Frontend) | Guardado | Estado | Diagnóstico |
| :--- | :--- | :--- | :--- | :--- |
| **Environment Tag** | `environment` | ❌ NO | ⚠️ IGNORADO | Falta columna `environment` en DB. |
| **Privacy Mode** | `privacyMode` | ❌ NO | ⚠️ IGNORADO | Falta columna `privacy_mode` en DB. |
| **Audit Logs** | `auditLogEnabled` | ❌ NO | ⚠️ IGNORADO | Falta columna `audit_log_enabled` en DB. |

## 3. Conclusión
**Prueba Fallida (0% Cobertura)**.
La funcionalidad de "Gobierno" es totalmente cosmética.
Aunque los campos están definidos en el frontend y mapeados en el router, la base de datos carece de la estructura para almacenarlos.

**Acción Requerida**: Crear migración para agregar las 5 columnas faltantes a la tabla `agent_configs`.
