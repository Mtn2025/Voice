-- Migration Script: Add Missing Columns to agent_configs Table
-- Date: 2026-01-10
-- Purpose: Add voice_language fields that were added to schema but missing in database

-- Add voice_language to base profile
ALTER TABLE agent_configs 
ADD COLUMN IF NOT EXISTS voice_language VARCHAR DEFAULT 'es-MX';

-- Note: The following columns were already added in previous migration:
-- - tts_provider_phone
-- - voice_language_phone  
-- - background_sound_phone
-- - tts_provider_telnyx
-- - voice_language_telnyx
-- - background_sound_telnyx
-- - background_sound_url_telnyx

-- Verify all columns exist
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'agent_configs'
AND column_name IN (
    'voice_language',
    'tts_provider_phone',
    'voice_language_phone',
    'background_sound_phone',
    'tts_provider_telnyx',
    'voice_language_telnyx',
    'background_sound_telnyx',
    'background_sound_url_telnyx'
)
ORDER BY column_name;
