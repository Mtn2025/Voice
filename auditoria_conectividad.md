# Auditoría de Conectividad (Webhooks & WebSocket)
*Auditoría realizada el 2026-01-26*

## 1. Puntos de Entrada (Endpoints)

### Twilio
- **Webhook URL**: `POST/GET /api/v1/twilio/incoming-call`
    - **Función**: Responde con TwiML para conectar la llamada al WebSocket.
    - **Seguridad**: `require_twilio_signature` (HMAC validation).
    - **Rate Limit**: 30 req/min por IP.

### Telnyx
- **Webhook URL**: `POST /api/v1/telnyx/call-control`
    - **Función**: Maneja el ciclo de vida completo (Call Control v2).
    - **Eventos Soportados**:
        - `call.initiated`: Responde la llamada (`call_control_id` almacenado).
        - `call.answered`: Inicia el stream de audio.
        - `streaming.started`/`stopped`: Control de flujo.
        - `call.hangup`: Limpieza de recursos.
    - **Seguridad**: `require_telnyx_signature` (Ed25519 validation).
    - **Rate Limit**: 50 req/min por IP.

### WebSocket (Media Stream)
- **URL**: `WS /api/v1/ws/media-stream`
- **Protocolos Soportados**:
    - `twilio` (Stream de Twilio Media)
    - `telnyx` (Stream de Telnyx)
    - `browser` (Simulador de cliente)
- **Codificación**:
    - Entrante: PCMU/PCMA @ 8000Hz (Telnyx/Twilio), PCM @ 16000Hz (Browser).
    - Saliente: Ajustada según cliente.

## 2. Integraciones Externas Configurales
- **Webhook Saliente (End-of-Call)**:
    - **Config**: `configs.browser.webhook_url`
    - **Trigger**: Al finalizar la llamada (BD `end_call`).
    - **Payload**: JSON con resumen de llamada y transcripción.
- **CRM (Baserow)**:
    - **Config**: `baserow_token`, `baserow_table_id`.
    - **Trigger**: Al detectar intención de "agendar" o finalizar.

## 3. Estado Actual
- **Ruteo**: Definido en `app/api/routes.py`.
- **Orquestación**: `app/core/orchestrator.py` maneja la lógica de negocio una vez conectado el socket.
- **Estado**: ✅ ACTIVO y SEGURO.
