# Inventario de Herramientas Avanzadas & CRM
*Auditoría realizada el 2026-01-26*

Este inventario detalla los controles disponibles en la pestaña `Avanzado` (`tab_advanced.html`).

## 1. Gestión de Llamada (Global)
- **Duración Máxima**:
    - Input Numérico (segundos).
    - Límite duro para desconexión automática.
    - Default: 600s.
- **Timeout Inactividad**:
    - Slider: 5 a 60 segundos.
    - Tiempo de silencio antes de colgar/preguntar "sigues ahí?".
- **Mensaje Inactividad**:
    - Texto que dice el bot antes de colgar por timeout.
- **Reintentos Máximos**:
    - Cuántas veces el bot intenta recuperar al usuario inactivo.

## 2. Configuración Telnyx (Only)
- **Grabar Llamada**:
    - Checkbox: Habilita grabación dual-channel en Telnyx.
- **AMD Config** (Answering Machine Detection):
    - Selector: `Disabled` / `Premium`.
    - Detección de buzón de voz.

## 3. Integraciones de Negocio
### CRM (Baserow)
Conexión directa a base de datos No-Code.
- **Token API**: Credencial de Baserow.
- **Table ID**: Identificador de la tabla de leads/contactos.
- **Habilitar Integración**: Toggle global.

### Webhook (Event Driven)
Notificación a sistemas externos (Make/Zapier/n8n).
- **Webhook URL**: Endpoint POST al finalizar llamada.
    - Envía: `transcript`, `summary`, `duration`, `sentiment`.
- **Secret Key**: Firma para validar autenticidad (HMAC opcional).

## 4. Estado de Implementación
- **Frontend**: Completo (`tab_advanced.html`).
- **Backend**:
    - CRM: `app/services/baserow.py`
    - Webhook: `app/services/webhook.py`
    - Lógica: `app/core/orchestrator.py` invoca estos servicios al evento `STOP`.
