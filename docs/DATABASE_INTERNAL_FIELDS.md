# Database Internal Fields Documentation

**Fecha**: 31 de Enero, 2026  
**Total Campos Internos**: 143  
**Modelo**: `AgentConfig` (app/db/models.py)

---

## Propósito

Este documento documenta los 143 campos internos de `AgentConfig` que **NO están expuestos en los schemas Pydantic** (browser/twilio/telnyx_schemas.py) pero que **SON utilizados activamente en el backend**.

Estos campos se configuran programáticamente, no a través de la UI/API.

---

## Clasificación por Grupo Funcional

### 1. STT Advanced Features (27 columnas)

**Propósito**: Configuración avanzada para providers STT (Deepgram, Azure)  
**Ubicación**: `app/adapters/outbound/stt/{azure,deepgram}_stt_adapter.py`  
**Perfiles**: Browser, Phone, Telnyx

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `stt_model` | VARCHAR | Modelo STT (e.g., "nova-2" para Deepgram) |
| `stt_keywords` | JSON | Keywords boosting para reconocimiento |
| `stt_silence_timeout` | INTEGER | Timeout de silencio en ms |
| `stt_utterance_end_strategy` | VARCHAR | Estrategia de detección de fin de frase |
| `stt_punctuation` | BOOLEAN | Habilitar puntuación automática |
| `stt_profanity_filter` | BOOLEAN | Filtro de lenguaje inapropiado |
| `stt_smart_formatting` | BOOLEAN | Formateo inteligente (fechas, números) |
| `stt_diarization` | BOOLEAN | Separación de hablantes |
| `stt_multilingual` | BOOLEAN | Detección multi-idioma |

**Nota**: Estos campos existen para los 3 perfiles con sufijos `_phone` y `_telnyx`.

---

### 2. Flow Control & VAD (12 columnas)

**Propósito**: Control de VAD (Voice Activity Detection) y flujo de conversación  
**Ubicación**: `app/processors/logic/vad.py`, `app/core/orchestrator.py`  
**Crítico**: SÍ - errores aquí afectan detección de voz

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `voice_sensitivity` | INTEGER | Sensitividad RMS para detección de voz |
| `voice_sensitivity_phone` | INTEGER | Sensitividad RMS (Phone) |
| `voice_sensitivity_telnyx` | INTEGER | Sensitividad RMS (Telnyx) |
| `vad_threshold` | FLOAT | Umbral VAD (0.0-1.0) |
| `vad_threshold_phone` | FLOAT | Umbral VAD (Phone) |
| `vad_threshold_telnyx` | FLOAT | Umbral VAD (Telnyx) - **EXPUESTO EN UI** |
| `initial_silence_timeout_ms` | INTEGER | Timeout de silencio inicial |
| `initial_silence_timeout_ms_phone` | INTEGER | Timeout inicial (Phone) |
| `initial_silence_timeout_ms_telnyx` | INTEGER | Timeout inicial (Telnyx) |

**Razón de mantener**: Críticas para timing de conversación.

---

### 3. Barge-In & Interruptions (9 columnas)

**Propósito**: Sistema de interrupciones del usuario  
**Ubicación**: `app/processors/logic/llm.py` (interruption detection)  
**Status**: Implementado pero no expuesto en UI

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `barge_in_enabled` | BOOLEAN | Habilitar interrupciones |
| `barge_in_enabled_phone` | BOOLEAN | Interrupciones (Phone) |
| `barge_in_enabled_telnyx` | BOOLEAN | Interrupciones (Telnyx) |
| `interruption_sensitivity` | FLOAT | Sensitividad para detectar interrupción |
| `interruption_sensitivity_phone` | FLOAT | Sensitividad (Phone) |
| `interruption_sensitivity_telnyx` | FLOAT | Sensitividad (Telnyx) |
| `interruption_phrases` | JSON | Frases que siempre se consideran interrupción |
| `interruption_phrases_phone` | JSON | Frases (Phone) |
| `interruption_phrases_telnyx` | JSON | Frases (Telnyx) |

**Razón de mantener**: Funcionalidad implementada, puede exponerse en futuro.

---

### 4. Pacing & Naturalness (12 columnas)

**Propósito**: Control de timing y naturalidad de conversación  
**Ubicación**: `app/processors/logic/humanizer.py`, `app/core/orchestrator.py`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `response_delay_seconds` | FLOAT | Delay antes de responder (naturalidad) |
| `response_delay_seconds_phone` | FLOAT | Delay (Phone) |
| `response_delay_seconds_telnyx` | FLOAT | Delay (Telnyx) |
| `wait_for_greeting` | BOOLEAN | Esperar saludo del usuario |
| `wait_for_greeting_phone` | BOOLEAN | Wait greeting (Phone) |
| `wait_for_greeting_telnyx` | BOOLEAN | Wait greeting (Telnyx) |
| `hyphenation_enabled` | BOOLEAN | Habilitar guiones en pronunciación |
| `hyphenation_enabled_phone` | BOOLEAN | Hyphenation (Phone) |
| `hyphenation_enabled_telnyx` | BOOLEAN | Hyphenation (Telnyx) |
| `end_call_phrases` | JSON | Frases que terminan la llamada |
| `end_call_phrases_phone` | JSON | End phrases (Phone) |
| `end_call_phrases_telnyx` | JSON | End phrases (Telnyx) |

**Razón de mantener**: Usadas para humanización de respuestas.

---

### 5. CRM & Webhooks (5 columnas)

**Propósito**: Integración CRM y webhooks externos  
**Ubicación**: `app/core/managers/crm_manager.py`, `app/routers/config_router.py`  
**Status**: FUNCIONAL en producción

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `crm_enabled` | BOOLEAN | Habilitar integración CRM |
| `baserow_token` | VARCHAR | Token API de Baserow |
| `baserow_table_id` | INTEGER | ID de tabla Baserow |
| `webhook_url` | VARCHAR | URL para webhooks post-llamada |
| `webhook_secret` | VARCHAR | Secret para validar webhooks |

**Razón de mantener**: En uso activo para integración CRM.

---

### 6. Tools & Function Calling (24+ columnas)

**Propósito**: Infraestructura de function calling (LLM tools)  
**Ubicación**: `app/processors/logic/llm.py`  
**Plan**: Integración con n8n

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tools_async` | BOOLEAN | Ejecutar tools de forma async |
| `tools_schema_phone` | JSON | Schema de tools (Phone) |
| `tools_schema_telnyx` | JSON | Schema de tools (Telnyx) |
| `async_tools_phone` | BOOLEAN | Async tools (Phone) |
| `async_tools_telnyx` | BOOLEAN | Async tools (Telnyx) |
| `tool_server_url` | VARCHAR | URL del servidor de tools |
| `tool_server_url_phone` | VARCHAR | URL (Phone) |
| `tool_server_url_telnyx` | VARCHAR | URL (Telnyx) |
| `tool_server_secret` | VARCHAR | Secret para auth con tool server |
| `tool_server_secret_phone` | VARCHAR | Secret (Phone) |
| `tool_server_secret_telnyx` | VARCHAR | Secret (Telnyx) |
| `tool_timeout_ms` | INTEGER | Timeout para llamadas de tools |
| `tool_timeout_ms_phone` | INTEGER | Timeout (Phone) |
| `tool_timeout_ms_telnyx` | INTEGER | Timeout (Telnyx) |
| `tool_retry_count` | INTEGER | Reintentos en caso de error |
| `tool_retry_count_phone` | INTEGER | Retries (Phone) |
| `tool_retry_count_telnyx` | INTEGER | Retries (Telnyx) |
| `tool_error_msg` | TEXT | Mensaje de error personalizado |
| `tool_error_msg_phone` | TEXT | Error msg (Phone) |
| `tool_error_msg_telnyx` | TEXT | Error msg (Telnyx) |
| `redact_params` | JSON | Parámetros a ocultar en logs |
| `redact_params_phone` | JSON | Redact (Phone) |
| `redact_params_telnyx` | JSON | Redact (Telnyx) |
| `transfer_whitelist` | JSON | Números permitidos para transfer |
| `transfer_whitelist_phone` | JSON | Whitelist (Phone) |
| `transfer_whitelist_telnyx` | JSON | Whitelist (Telnyx) |
| `state_injection_enabled` | BOOLEAN | Habilitar inyección de estado dinámico |
| `state_injection_enabled_phone` | BOOLEAN | State injection (Phone) |
| `state_injection_enabled_telnyx` | BOOLEAN | State injection (Telnyx) |

**Razón de mantener**: Infraestructura para LLM function calling.

---

### 7. Call Features (6 columnas)

**Propósito**: Features telefónicas (recording, transfer, DTMF)  
**Ubicación**: Telephony adapters (Twilio/Telnyx)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `recording_enabled_phone` | BOOLEAN | Grabar llamadas (Phone) |
| `transfer_type_phone` | VARCHAR | Tipo de transferencia (warm/cold) |
| `transfer_type_telnyx` | VARCHAR | Tipo de transferencia (Telnyx) |
| `dtmf_generation_enabled_phone` | BOOLEAN | Generar DTMF (Phone) |
| `dtmf_generation_enabled_telnyx` | BOOLEAN | Generar DTMF (Telnyx) |
| `dtmf_listening_enabled_telnyx` | BOOLEAN | Escuchar DTMF - **EXPUESTO EN UI** |

**Razón de mantener**: Features estándar de telefonía.

---

### 8. Rate Limiting & Governance (11 columnas)

**Propósito**: Control de producción, rate limiting, governance  
**Ubicación**: Middleware (futuro), rate limiter

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `rate_limit_global` | INTEGER | Rate limit global (req/min) |
| `rate_limit_twilio` | INTEGER | Rate limit Twilio |
| `rate_limit_telnyx` | INTEGER | Rate limit Telnyx |
| `rate_limit_websocket` | INTEGER | Rate limit WebSocket |
| `limit_groq_tokens_per_min` | INTEGER | Límite Groq tokens/min |
| `limit_azure_requests_per_min` | INTEGER | Límite Azure req/min |
| `limit_twilio_calls_per_hour` | INTEGER | Límite Twilio calls/hour |
| `limit_telnyx_calls_per_hour` | INTEGER | Límite Telnyx calls/hour |
| `concurrency_limit` | INTEGER | Límite de llamadas concurrentes |
| `spend_limit_daily` | FLOAT | Límite de gasto diario (USD) |
| `environment` | VARCHAR | Environment tag (dev/staging/prod) |

**Razón de mantener**: Necesarias para escala y seguridad en producción.

---

### 9. Analysis & Post-Call (18 columnas)

**Propósito**: Análisis post-llamada, extracción de datos  
**Ubicación**: Post-call analytics pipeline (parcialmente implementado)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `analysis_prompt` | TEXT | Prompt para análisis post-llamada |
| `analysis_prompt_phone` | TEXT | Analysis (Phone) |
| `analysis_prompt_telnyx` | TEXT | Analysis (Telnyx) |
| `success_rubric` | TEXT | Criterios de éxito de llamada |
| `success_rubric_phone` | TEXT | Rubric (Phone) |
| `success_rubric_telnyx` | TEXT | Rubric (Telnyx) |
| `extraction_schema` | JSON | Schema para extracción estructurada |
| `extraction_schema_phone` | JSON | Extraction (Phone) |
| `extraction_schema_telnyx` | JSON | Extraction (Telnyx) |
| `sentiment_analysis_enabled` | BOOLEAN | Habilitar análisis de sentimiento |
| `sentiment_analysis_enabled_phone` | BOOLEAN | Sentiment (Phone) |
| `sentiment_analysis_enabled_telnyx` | BOOLEAN | Sentiment (Telnyx) |
| `transcript_format` | VARCHAR | Formato de transcripción |
| `cost_tracking_enabled` | BOOLEAN | Tracking de costos |
| `log_webhook_url` | VARCHAR | Webhook para logs |
| `pii_redaction_enabled` | BOOLEAN | Redactar PII de transcripts |
| `retention_days` | INTEGER | Días de retención de data |

**Razón de mantener**: Roadmap features para analytics.

---

### 10. System Metadata (12+ columnas)

**Propósito**: Metadata de sistema, enterprise features  
**Ubicación**: Sistema (RBAC, multi-tenant en futuro)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `is_active` | BOOLEAN | Config activa o archivada |
| `privacy_mode` | BOOLEAN | Modo privacidad (no guardar transcripts) |
| `audit_log_enabled` | BOOLEAN | Habilitar audit log |
| `audit_log_enabled_telnyx` | BOOLEAN | Audit log (Telnyx) - **EXPUESTO EN UI** |
| `custom_headers` | JSON | Headers HTTP personalizados |
| `sub_account_id` | VARCHAR | ID de sub-cuenta (multi-tenant) |
| `allowed_api_keys` | JSON | API keys permitidas |
| `encryption_enabled` | BOOLEAN | Encriptar data en reposo |
| `compliance_mode` | VARCHAR | Modo de compliance (HIPAA, GDPR) |

**Razón de mantener**: Future enterprise features.

---

### 11. Pronunciation Dictionary (3 columnas)

**Propósito**: Diccionario de pronunciación personalizada  
**Ubicación**: TTS adapters (Azure, ElevenLabs)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pronunciation_dictionary` | JSON | Dict de pronunciacion (Browser) |
| `pronunciation_dictionary_phone` | JSON | Dict (Phone) |
| `pronunciation_dictionary_telnyx` | JSON | Dict (Telnyx) |

**Ejemplo**: `{"2026": "dos mil veintiséis", "USD": "dólares"}`

**Razón de mantener**: Advanced TTS feature, puede exponerse en UI futuro.

---

### 12. Otros (4 columnas)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `extraction_model` | VARCHAR | Modelo LLM para extracción de datos |
| `name` | VARCHAR | Nombre de la configuración |
| `id` | INTEGER | ID primary key |

---

## Resumen por Uso

| Grupo | Columnas | Status | Acción |
|-------|----------|--------|--------|
| STT Advanced | 27 | Activo | Mantener |
| Flow Control & VAD | 12 | Crítico | Mantener |
| Barge-In | 9 | Implementado | Mantener |
| Pacing | 12 | Activo | Mantener |
| CRM & Webhooks | 5 | Producción | Mantener |
| Tools & Function Calling | 24+ | Infraestructura | Mantener |
| Call Features | 6 | Activo | Mantener |
| Rate Limiting | 11 | Planeado | Mantener |
| Analysis | 18 | Roadmap | Mantener |
| System Metadata | 12+ | Enterprise | Mantener |
| Pronunciation | 3 | Planeado | Mantener |
| Otros | 4 | Metadata | Mantener |

**Total**: 143 columnas internas **en uso activo o planeadas**.

---

## Recomendaciones

1. **NO ELIMINAR** ninguno de estos 143 campos
2. **Considerar exposición gradual** en UI para features avanzadas
3. **Plan de normalización (v3.0)**: Separar en tablas por perfil
4. **Documentar uso** en comentarios de código al implementar features nuevas

---

**Última actualización**: 31 Enero 2026  
**Mantenedor**: Sistema de Auditoría DB
