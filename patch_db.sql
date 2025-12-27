ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS interruption_threshold_phone INTEGER DEFAULT 2;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS voice_speed_phone FLOAT DEFAULT 0.9;
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS silence_timeout_ms_phone INTEGER DEFAULT 1200;
