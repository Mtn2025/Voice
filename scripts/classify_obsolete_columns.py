"""
Manual review and classification of 163 obsolete columns.
Based on pattern recognition and code knowledge.
"""

import json
from pathlib import Path

def classify_obsolete_columns():
    """
    Classify 163 obsolete columns into action categories.
    
    Categories:
    - ELIMINAR: No used anywhere, safe to delete
    - MANTENER_SCHEMA: Used in backend, add to schema
    - DOCUMENTAR: Internal use only, not user-facing
    """
    
    # Load obsolete columns
    with open("audit/columns_classified.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    obsolete = data.get("obsolete", [])
    
    results = {
        "ELIMINAR": [],          # Safe to delete
        "MANTENER_SCHEMA": [],   # Add to schema
        "DOCUMENTAR": [],         # Keep but document as internal
        "SUMMARY": {}
    }
    
    # Pattern-based classification
    for col in obsolete:
        column_name = col["column"]
        profile = col["profile"]
        
        # Category 1: STT Advanced Features (Deepgram-specific, not exposed in UI)
        if any(x in column_name for x in [
            "stt_model", "stt_keywords", "stt_silence_timeout",
            "stt_utterance_end_strategy", "stt_punctuation",
            "stt_profanity_filter", "stt_smart_formatting",
            "stt_diarization", "stt_multilingual"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Deepgram STT advanced features - used in backend but not exposed in UI",
                "action": "Keep in DB, document as internal"
            })
        
        # Category 2: Pronunciation Dictionary (Internal feature)
        elif "pronunciation_dictionary" in column_name:
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Advanced TTS feature - used internally",
                "action": "Keep for future UI exposure"
            })
        
        # Category 3: Twilio-specific UI fields (belongs in config_router/dashboard)
        elif column_name in [
            "twilio_machine_detection", "twilio_record",
            "twilio_recording_channels", "twilio_trim_silence"
        ]:
            results["MANTENER_SCHEMA"].append({
                **col,
                "reason": "Twilio-specific configuration - should be in TwilioConfigUpdate schema",
                "action": "Add to twilio_schemas.py"
            })
        
        # Category 4: Global metadata (used in models, not in schemas)
        elif column_name in ["is_active", "name", "id"]:
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Model metadata - not part of user configuration",
                "action": "Keep as is"
            })
        
        # Category 5: Initial silence timeout (used in orchestrator)
        elif "initial_silence_timeout_ms" in column_name:
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Used in VoiceOrchestrator - internal timing control",
                "action": "Keep in DB, not user-facing"
            })
        
        # Category 6: Legacy/experimental features
        elif column_name in [
            "voice_id_manual", "input_min_characters", "punctuation_boundaries",
            "segmentation_max_time", "segmentation_strategy"
        ]:
            results["ELIMINAR"].append({
                **col,
                "reason": "Deprecated/unused experimental feature",
                "action": "Safe to delete in migration"
            })
        
        # Category 7: Flow control (used in orchestrator)
        elif any(x in column_name for x in [
            "voice_sensitivity", "vad_threshold",
            "barge_in", "interruption_sensitivity", "interruption_phrases"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Flow control features - used in backend processors",
                "action": "Keep, may expose in UI later"
            })
        
        # Category 8: Advanced call features (AMD, voicemail detection)
        elif any(x in column_name for x in [
            "voicemail_detection", "voicemail_message",
            "machine_detection_sensitivity"
        ]):
            results["MANTENER_SCHEMA"].append({
                **col,
                "reason": "Advanced telephony features - should be configurable",
                "action": "Add to profile schemas"
            })
        
        # Category 9: Pacing & naturalness
        elif any(x in column_name for x in [
            "response_delay_seconds", "wait_for_greeting",
            "hyphenation_enabled", "end_call_phrases"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Conversation flow tuning - internal use",
                "action": "Keep for fine-tuning"
            })
        
        # Category 10: CRM & Webhooks (used in routers/services)
        elif any(x in column_name for x in [
            "crm_enabled", "baserow", "webhook_url", "webhook_secret"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Integration features - used in CRM manager and webhooks",
                "action": "Keep, already functional"
            })
        
        # Category 11: Telnyx credentials (should be in env or schema)
        elif "telnyx_api_user" in column_name:
            results["ELIMINAR"].append({
                **col,
                "reason": "Credential field - use telnyx_api_key instead",
                "action": "Delete"
            })
        
        # Category 12: Tools & Function Calling
        elif any(x in column_name for x in [
            "tools_async", "tool_server", "tool_timeout",
            "tool_retry", "tool_error_msg", "redact_params",
            "transfer_whitelist", "state_injection",
            "tools_schema", "async_tools"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Function calling infrastructure - used in LLM processor",
                "action": "Keep for n8n integration"
            })
        
        # Category 13: Call features (transfer, DTMF, recording)
        elif any(x in column_name for x in [
            "recording_enabled", "recording_channels",
            "transfer_type", "dtmf_generation", "dtmf_listening"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Telephony call features - used in adapters",
                "action": "Keep for telephony providers"
            })
        
        # Category 14: Rate limiting & governance
        elif any(x in column_name for x in [
            "rate_limit", "limit_groq", "limit_azure",
            "limit_twilio", "limit_telnyx",
            "concurrency_limit", "spend_limit", "environment"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "System governance - used in middleware/rate limiter",
                "action": "Keep for production safety"
            })
        
        # Category 15: Analysis & post-call
        elif any(x in column_name for x in [
            "analysis_prompt", "success_rubric", "extraction_schema",
            "sentiment_analysis", "transcript_format", "cost_tracking",
            "log_webhook", "pii_redaction", "retention_days"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Post-call analysis features - partially implemented",
                "action": "Keep for analytics pipeline"
            })
        
        # Category 16: Extra settings (catch-all JSON field)
        elif "extra_settings" in column_name:
            results["ELIMINAR"].append({
                **col,
                "reason": "Unused catch-all field",
                "action": "Delete, use specific fields instead"
            })
        
        # Category 17: System metadata
        elif any(x in column_name for x in [
            "privacy_mode", "audit_log", "custom_headers",
            "sub_account_id", "allowed_api_keys",
            "encryption", "compliance"
        ]):
            results["DOCUMENTAR"].append({
                **col,
                "reason": "System metadata - for enterprise features",
                "action": "Keep for future RBAC/security"
            })
        
        # Category 18: Remaining (unclassified - review needed)
        else:
            # Default: document
            results["DOCUMENTAR"].append({
                **col,
                "reason": "Unclassified - manual review needed",
                "action": "Review individually"
            })
    
    # Generate summary
    results["SUMMARY"] = {
        "total_obsolete": len(obsolete),
        "to_delete": len(results["ELIMINAR"]),
        "to_add_schema": len(results["MANTENER_SCHEMA"]),
        "to_document": len(results["DOCUMENTAR"]),
        "deletion_percentage": f"{len(results['ELIMINAR'])/len(obsolete)*100:.1f}%"
    }
    
    # Export
    output = Path("audit/obsolete_columns_classified.json")
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print("=" * 80)
    print("OBSOLETE COLUMNS CLASSIFICATION")
    print("=" * 80)
    print(f"\n📊 Total Obsolete: {results['SUMMARY']['total_obsolete']}")
    print(f"\n🗑️  ELIMINAR (safe to delete): {results['SUMMARY']['to_delete']}")
    print(f"✅ MANTENER_SCHEMA (add to schemas): {results['SUMMARY']['to_add_schema']}")
    print(f"📋 DOCUMENTAR (keep as internal): {results['SUMMARY']['to_document']}")
    print(f"\n💾 Deletion potential: {results['SUMMARY']['deletion_percentage']}")
    print(f"\n✅ Classification exported: {output}")
    
    return results

if __name__ == "__main__":
    results = classify_obsolete_columns()
