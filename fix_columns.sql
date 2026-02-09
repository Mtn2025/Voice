
-- Reset columns that seem to be invisible to uvicorn
ALTER TABLE agent_configs DROP COLUMN IF EXISTS privacy_mode_phone;
ALTER TABLE agent_configs ADD COLUMN privacy_mode_phone BOOLEAN DEFAULT FALSE;

ALTER TABLE agent_configs DROP COLUMN IF EXISTS environment_phone;
ALTER TABLE agent_configs ADD COLUMN environment_phone VARCHAR;

ALTER TABLE agent_configs DROP COLUMN IF EXISTS barge_in_enabled;
ALTER TABLE agent_configs ADD COLUMN barge_in_enabled BOOLEAN DEFAULT TRUE;

ALTER TABLE agent_configs DROP COLUMN IF EXISTS barge_in_enabled_phone;
ALTER TABLE agent_configs ADD COLUMN barge_in_enabled_phone BOOLEAN DEFAULT TRUE;

ALTER TABLE agent_configs DROP COLUMN IF EXISTS interruption_sensitivity;
ALTER TABLE agent_configs ADD COLUMN interruption_sensitivity FLOAT DEFAULT 0.5;

ALTER TABLE agent_configs DROP COLUMN IF EXISTS interruption_phrases;
ALTER TABLE agent_configs ADD COLUMN interruption_phrases VARCHAR;

-- environment_telnyx was already done, but to be safe and consistent order:
ALTER TABLE agent_configs DROP COLUMN IF EXISTS environment_telnyx;
ALTER TABLE agent_configs ADD COLUMN environment_telnyx VARCHAR;

ALTER TABLE agent_configs DROP COLUMN IF EXISTS privacy_mode_telnyx;
ALTER TABLE agent_configs ADD COLUMN privacy_mode_telnyx BOOLEAN DEFAULT FALSE;

-- Force update to ensure visibility (vacuous update)
UPDATE agent_configs SET name=name;
