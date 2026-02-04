# Reporte de Simulación Exhaustiva: Pestaña Campaigns

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la integridad, persistencia y funcionalidad de los controles de la Pestaña "Campaigns".
**Alcance:** 4 Controles (Integraciones) + 1 Acción (Iniciar Campaña).

## 1. Metodología
*   **Script**: `tests/manual/verify_campaigns_exhaustive.py`
*   **Fuente de Verdad**: Imágenes de UI + `store.v2.js`.
*   **Método**: Inyección de configuración + Intento de Upload al endpoint `/api/campaigns/start`.

## 2. Resultados Detallados

### Sección 1: Integraciones (Configuración)
| Control (UI) | Key (Frontend) | Guardado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- |
| **Integración CRM (Baserow)** | `crmEnabled` | ✅ SÍ | ✅ OK | Persistido correctamente. |
| **Integración Webhook (URL)** | `webhookUrl` | ✅ SÍ | ✅ OK | Persistido correctamente. |
| **Autenticación Webhook** | `webhookSecret` | ✅ SÍ | ✅ OK | Persistido correctamente. |
| **Nombre de Campaña** | `campaignName` | N/A | ⚠️ UI | Variable de estado Vue (Transient). No persiste en DB. |
| **Archivo CSV** | `campaignFile` | N/A | ⚠️ UI | Variable de estado Vue (Transient). |

### Sección 2: Acción "Iniciar Campaña" (CRÍTICO)
| Acción | Endpoint Objetivo | Resultado | Estado | Diagnóstico |
| :--- | :--- | :--- | :--- | :--- |
| **Click "Iniciar Campaña"** | `POST /api/campaigns/start` | ❌ 404 Not Found | 🚨 ERROR | El endpoint **NO EXISTE** en el backend. |

## 3. Diagnóstico Técnico
Si bien la configuración de integraciones (CRM/Connectors) comparte lógica con la pestaña Tools y funciona correctamente, la funcionalidad principal de **"Campaign Execution" está incompleta**.
*   **Frontend**: `api.js` intenta llamar a `/api/campaigns/start`.
*   **Backend**: No existe ningún router (`routes/campaigns.py` o similar) registrado para manejar esta ruta.
*   **Consecuencia**: El botón "Iniciar Campaña" es funcionalmente inoperante.

## 4. Conclusiones
*   **Configuración**: ✅ APROBADA (Integraciones persisten).
*   **Ejecución**: ❌ FALLIDA (Endpoint faltante).

Se requiere implementar el router de campañas (`POST /api/campaigns/start`) para procesar el CSV y encolar las llamadas en el `Dialer`.
