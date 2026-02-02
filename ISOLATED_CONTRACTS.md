# Isolated Contracts: Profile Specifics

Este documento define los elementos que **NUNCA** deben compartirse entre perfiles. Cualquier lógica compartida que involucre estos elementos es una violación de aislamiento y riesgo de seguridad/estabilidad.

## 1. Webhooks y Entry Points

| Elemento | Perfil Dueño | Archivo Aislado | Descripción |
| :--- | :--- | :--- | :--- |
| **Route /twilio/incoming-call** | Twilio | `app/api/routes_v2.py` (Debería ser aislado) | Devuelve TwiML XML. No usable por Telnyx/Browser. |
| **Route /telnyx/call-control** | Telnyx | `app/api/routes_v2.py` | Maneja eventos JSON de Telnyx `call.initiated`, etc. Lógica de estado compleja. |
| **Verification Signature** | Twilio/Telnyx | `app/core/webhook_security.py` | `require_twilio_signature` vs `require_telnyx_signature`. Nunca mezclar claves. |

## 2. Estados Técnicos y Protocolos

| Elemento | Perfil Dueño | Comportamiento Aislado |
| :--- | :--- | :--- |
| **Audio Format** | **Browser** | PCM 16kHz, 16-bit, Mono (Optimizado para Web Audio API). |
| **Audio Format** | **Twilio** | Mulaw 8kHz (Phone Standard). |
| **Audio Format** | **Telnyx** | PCMA/PCMU 8kHz (variable, negociado en `start`). |
| **Transport Protocol** | **Browser** | WebSocket directo con JSON events custom (`start`, `media`). |
| **Transport Protocol** | **Twilio** | WebSocket con eventos Twilio (`start`, `media` con `streamSid`, `mark`). |
| **Transport Protocol** | **Telnyx** | WebSocket con eventos Telnyx (`media` con `track: inbound`). |
| **Latencia/Pacing** | **Phone** | Requiere `Voice Pacing` artificial (400ms+) para evitar interrumpir por latencia de red 4G/5G. |
| **Latencia/Pacing** | **Browser** | `Voice Pacing` = 0ms. Respuesta inmediata deseada. |

## 3. Configuraciones Específicas (Isolated Configs)
Aunque vivan en la misma tabla DB, estos campos son **propiedad exclusiva** del perfil.

| Campo Config | Dueño | Uso Prohibido |
| :--- | :--- | :--- |
| `twilio_account_sid`, `twilio_auth_token` | Twilio | NO leer en lógica de Telnyx o Browser. |
| `telnyx_api_key`, `telnyx_connection_id` | Telnyx | NO leer en lógica de Twilio. |
| `amd_config_telnyx` | Telnyx | Configuración de Answering Machine Detection (propia de Telnyx). |
| `enable_krisp_telnyx` | Telnyx | Supresión de ruido propia de Telnyx. |

## 4. Dashboard y UI (Simulador)

| Elemento | Contexto | Aislamiento |
| :--- | :--- | :--- |
| **Panel Simulador** | Dashboard (Right Sidebar) | **Solo visible en modo Browser/Test**. No tiene sentido para llamadas telefónicas reales (excepto logs). |
| **Botón "Test Outbound"** | Dashboard | Actualmente hardcoded a Telnyx (Violación reportada). Debería ser contextual o tener selector. |
| **Voice Preview** | Voice Tab | Usa el perfil "Browser" implícitamente para reproducir audio en el navegador del admin. |
