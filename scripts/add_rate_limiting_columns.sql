-- =============================================================================
-- Migration Script: Add Rate Limiting Configuration to agent_configs
-- =============================================================================
-- Punto A3 Extensión: Configuración Dinámica de Rate Limiting
-- Ejecutar con: psql -U postgres -d voice_db -f add_rate_limiting_columns.sql
-- O desde pgAdmin/DBeaver
-- =============================================================================

-- Rate Limiting por Endpoint (requests/minuto)
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_global INTEGER DEFAULT 200;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_twilio INTEGER DEFAULT 30;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_telnyx INTEGER DEFAULT 50;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_websocket INTEGER DEFAULT 100;

-- Provider Limits (Límites de consumo por proveedor)
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_groq_tokens_per_min INTEGER DEFAULT 100000;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_azure_requests_per_min INTEGER DEFAULT 100;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_twilio_calls_per_hour INTEGER DEFAULT 100;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_telnyx_calls_per_hour INTEGER DEFAULT 100;

-- Comentarios para documentación
COMMENT ON COLUMN agent_configs.rate_limit_global IS 'Límite global de requests/minuto para todos los endpoints (default: 200)';
COMMENT ON COLUMN agent_configs.rate_limit_twilio IS 'Límite de requests/minuto para webhook de Twilio (default: 30)';
COMMENT ON COLUMN agent_configs.rate_limit_telnyx IS 'Límite de requests/minuto para webhook de Telnyx (default: 50)';
COMMENT ON COLUMN agent_configs.rate_limit_websocket IS 'Límite de conexiones WebSocket/minuto (default: 100)';
COMMENT ON COLUMN agent_configs.limit_groq_tokens_per_min IS 'Límite de tokens/minuto para Groq LLM (default: 100000)';
COMMENT ON COLUMN agent_configs.limit_azure_requests_per_min IS 'Límite de requests/minuto para Azure STT/TTS (default: 100)';
COMMENT ON COLUMN agent_configs.limit_twilio_calls_per_hour IS 'Límite de llamadas/hora en Twilio para monitoreo (default: 100)';
COMMENT ON COLUMN agent_configs.limit_telnyx_calls_per_hour IS 'Límite de llamadas/hora en Telnyx para monitoreo (default: 100)';
