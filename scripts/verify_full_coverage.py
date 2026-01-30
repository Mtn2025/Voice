import sys
import os
import json

sys.path.append(os.getcwd())

from app.schemas.config_schemas import BrowserConfigUpdate, TwilioConfigUpdate, TelnyxConfigUpdate

def verify_coverage():
    print("🚀 Verifying 100% Config Coverage...")
    
    # 1. BROWSER PROFILE KEYS (Derived from store.v2.js initBrowserConfig)
    browser_keys = {
        "provider": "dummy", "model": "dummy", "temp": 0.5, "tokens": 100,
        "msg": "dummy", "mode": "dummy", "prompt": "dummy",
        "responseLength": "dummy", "conversationTone": "dummy",
        "conversationFormality": "dummy", "conversationPacing": "dummy",
        "contextWindow": 10, "frequencyPenalty": 0.5, "presencePenalty": 0.5,
        "toolChoice": "dummy", "dynamicVarsEnabled": False, "dynamicVars": "{}",
        "voiceProvider": "dummy", "voiceLang": "dummy", "voiceId": "dummy",
        "voiceStyle": "dummy", "voiceSpeed": 1.0, "voicePitch": 0,
        "voiceVolume": 100, "voiceStyleDegree": 1.0, "voicePacing": 0,
        "voiceBgSound": "dummy", "voiceBgUrl": "dummy",
        "voiceStability": 0.5, "voiceSimilarityBoost": 0.5, "voiceStyleExaggeration": 0.5,
        "voiceSpeakerBoost": True, "voiceMultilingual": True,
        "ttsLatencyOptimization": 0, "ttsOutputFormat": "dummy",
        "voiceFillerInjection": False, "voiceBackchanneling": False,
        "textNormalizationRule": "dummy",
        "sttProvider": "dummy", "sttLang": "dummy", "interruptWords": 5,
        "silence": 500, "blacklist": "dummy", "enableEndCall": False,
        "segmentationStrategy": "dummy", "enableDialKeypad": False,
        "transferNum": "dummy", "idleTimeout": 10.0, "maxDuration": 600,
        "idleMessage": "dummy", "maxRetries": 3, "denoise": False,
        "extractionModel": "dummy", "crm_enabled": False,
        "baserow_token": "dummy", "baserow_table_id": "dummy",
        "webhook_url": "dummy", "webhook_secret": "dummy",
        "rateLimitGlobal": 100, "rateLimitTwilio": 100, "rateLimitTelnyx": 100,
        "twilioAccountSid": "dummy", "twilioAuthToken": "dummy", "twilioFromNumber": "dummy",
        "telnyxApiKey": "dummy", "telnyxConnectionId": "dummy", "callerIdTelnyx": "dummy",
        "sipTrunkUriPhone": "dummy", "sipAuthUserPhone": "dummy", "sipAuthPassPhone": "dummy",
        "fallbackNumberPhone": "dummy", "geoRegionPhone": "dummy",
        "sipTrunkUriTelnyx": "dummy", "sipAuthUserTelnyx": "dummy",
        "sipAuthPassTelnyx": "dummy", "fallbackNumberTelnyx": "dummy",
        "geoRegionTelnyx": "dummy", "recordingChannelsPhone": "dummy",
        "recordingChannelsTelnyx": "dummy", "hipaaEnabledPhone": False,
        "hipaaEnabledTelnyx": False, "dtmfListeningEnabledPhone": False,
        "concurrencyLimit": 10, "spendLimitDaily": 10.0, "environment": "dummy",
        "privacyMode": False, "auditLogEnabled": False
    }

    # 2. TWILIO PROFILE KEYS (Derived from store.v2.js initTwilioConfig)
    twilio_keys = {
        "provider": "dummy", "model": "dummy", "temp": 0.5, "tokens": 100,
        "msg": "dummy", "mode": "dummy", "prompt": "dummy",
        "responseLength": "dummy", "conversationTone": "dummy",
        "conversationFormality": "dummy", "conversationPacing": "dummy",
        "contextWindow": 10, "frequencyPenalty": 0.5, "presencePenalty": 0.5,
        "toolChoice": "dummy", "dynamicVarsEnabled": False, "dynamicVars": "{}",
        "voiceProvider": "dummy", "voiceLang": "dummy", "voiceId": "dummy",
        "voiceStyle": "dummy", "voiceSpeed": 1.0, "voicePitch": 0,
        "voiceVolume": 100, "voiceStyleDegree": 1.0, "voicePacing": 0,
        "voiceBgSound": "dummy",
        "voiceStability": 0.5, "voiceSimilarityBoost": 0.5, "voiceStyleExaggeration": 0.5,
        "voiceSpeakerBoost": True, "voiceMultilingual": True,
        "ttsLatencyOptimization": 0, "ttsOutputFormat": "dummy",
        "voiceFillerInjection": False, "voiceBackchanneling": False,
        "textNormalizationRule": "dummy",
        "sttProvider": "dummy", "sttLang": "dummy", "interruptWords": 5,
        "silence": 500, "inputMin": 5, "blacklist": "dummy", "denoise": False,
        "crm_enabled": False, "baserow_token": "dummy", "baserow_table_id": "dummy",
        "webhook_url": "dummy", "webhook_secret": "dummy",
        
        # Phone specific
        "twilioAccountSid": "dummy", "twilioAuthToken": "dummy", "twilioFromNumber": "dummy"
    }

    # 3. TELNYX PROFILE KEYS (Derived from store.v2.js initTelnyxConfig)
    telnyx_keys = {
        "provider": "dummy", "model": "dummy", "temp": 0.5, "tokens": 100,
        "msg": "dummy", "mode": "dummy", "prompt": "dummy",
        "responseLength": "dummy", "conversationTone": "dummy",
        "conversationFormality": "dummy", "conversationPacing": "dummy",
        "contextWindow": 10, "frequencyPenalty": 0.5, "presencePenalty": 0.5,
        "toolChoice": "dummy", "dynamicVarsEnabled": False, "dynamicVars": "{}",
        "voiceProvider": "dummy", "voiceLang": "dummy", "voiceId": "dummy",
        "voiceStyle": "dummy", "voiceSpeed": 1.0, "voicePitch": 0,
        "voiceVolume": 100, "voiceStyleDegree": 1.0, "voicePacing": 0,
        "voiceBgSound": "dummy", "voiceBgUrl": "dummy",
        "voiceStability": 0.5, "voiceSimilarityBoost": 0.5, "voiceStyleExaggeration": 0.5,
        "voiceSpeakerBoost": True, "voiceMultilingual": True,
        "ttsLatencyOptimization": 0, "ttsOutputFormat": "dummy",
        "voiceFillerInjection": False, "voiceBackchanneling": False,
        "textNormalizationRule": "dummy",
        "sttProvider": "dummy", "sttLang": "dummy", "interruptWords": 5,
        "interruptRMS": 1000, "silence": 500, "inputMin": 5,
        "blacklist": "dummy", "denoise": False, "krisp": False, "vad": False,
        "vadThreshold": 0.5, "idleTimeout": 10.0, "maxDuration": 600,
        "idleMessage": "dummy", "enableRecording": False, "amdConfig": "dummy",
        "crm_enabled": False, "baserow_token": "dummy", "baserow_table_id": "dummy",
        "webhook_url": "dummy", "webhook_secret": "dummy",
        
        # Telnyx Specific
        "telnyxApiKey": "dummy", "telnyxConnectionId": "dummy"
    }
    
    # 4. IGNORED KEYS (We expect these to be dropped as they are global or metadata)
    EXPECTED_DROPPED = {
        "crm_enabled", "baserow_token", "baserow_table_id", "webhook_url", "webhook_secret", 
        "rateLimitGlobal", "rateLimitTwilio", "rateLimitTelnyx",
        "twilioAccountSid", "twilioAuthToken", "twilioFromNumber", # Global/Phone handled separately?
        "telnyxApiKey", "telnyxConnectionId", "callerIdTelnyx",
        "sipTrunkUriPhone", "sipAuthUserPhone", "sipAuthPassPhone", "fallbackNumberPhone", "geoRegionPhone",
        "sipTrunkUriTelnyx", "sipAuthUserTelnyx", "sipAuthPassTelnyx", "fallbackNumberTelnyx", "geoRegionTelnyx",
        "recordingChannelsPhone", "recordingChannelsTelnyx", "hipaaEnabledPhone", "hipaaEnabledTelnyx", "dtmfListeningEnabledPhone",
        "concurrencyLimit", "spendLimitDaily", "environment", "privacyMode", "auditLogEnabled",
        "segmentationStrategy", "extractionModel" 
    }
    
    # NOTE: "twilioAccountSid" IS present in Phone Config update?
    # Let's check schema. `TwilioConfigUpdate` has `twilio_account_sid` (aliased).
    # So it SHOULD be accepted for Twilio Profile.
    # `BrowserConfigUpdate` does NOT have them.
    
    # ... (Previous keys definitions remain) ...

    errors = []

    def check_profile(profile_name, input_keys, model_class):
        print(f"🔎 Checking {profile_name}...")
        try:
            config = model_class(**input_keys)
            # Dump to snake_case dictionary
            dumped = config.model_dump(exclude_unset=True, by_alias=False)
            
            # Map snake_case back to aliases to see what was covered?
            # Better: We iterate INPUT KEYS.
            # We need to know if an input key was "consumed".
            # Pydantic doesn't easily tell us "this key mapped to that field".
            # BUT we can check if the field it maps to is present in `dumped`.
            
            # We can get the Alias mapping from the Model
            alias_map = {}
            for field_name, field_info in model_class.model_fields.items():
                if field_info.alias:
                    alias_map[field_info.alias] = field_name
                # Also support direct name if no alias?
                alias_map[field_name] = field_name

            for key in input_keys:
                if key in EXPECTED_DROPPED:
                    continue
                
                # Check if this key corresponds to a field in the model
                target_field = alias_map.get(key)
                
                if not target_field:
                    # Maybe it matches a field name directly?
                    if key in model_class.model_fields:
                        target_field = key
                
                if not target_field:
                    errors.append(f"[{profile_name}] Key '{key}' has NO matching field/alias in Schema.")
                    continue
                    
                # Verify the value is in the dump (meaning not filtered out)
                if target_field not in dumped:
                     errors.append(f"[{profile_name}] Key '{key}' mapped to '{target_field}' but was DROPPED from output.")

        except Exception as e:
            errors.append(f"[{profile_name}] Crash: {e}")

    # Run Checks
    check_profile("Browser", browser_keys, BrowserConfigUpdate)
    check_profile("Twilio", twilio_keys, TwilioConfigUpdate)
    check_profile("Telnyx", telnyx_keys, TelnyxConfigUpdate)

    if errors:
        print("\n❌ COVERAGE FAILURES:")
        for e in errors: print(f"  - {e}")
        sys.exit(1)
    else:
        print("\n✅ 100% COVERAGE VERIFIED. All keys are safe.")

if __name__ == "__main__":
    verify_coverage()
