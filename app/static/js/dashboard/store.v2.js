import { api, csvValidator } from './api.js?v=ui_fix_1';
import { SimulatorMixin } from './simulator.v2.js?v=ui_fix_1';

export function dashboardStore() {
    return {
        ...SimulatorMixin, // Merge Simulator logic

        // Explicitly initialize reactive state (Redundant safety for caching issues)
        debugLogs: [],
        metrics: { llm_latency: '-', tts_latency: '-' },
        vadLevel: 0,
        isAgentSpeaking: false,

        // ==========================================
        // CORE DASHBOARD STATE
        // ==========================================
        activeTab: 'model',
        activeHistoryFilter: 'all',
        activeProfile: 'browser',
        showDebug: false, // UI Toggle for Debug Console
        serverConfig: {},

        // DATA HOLDERS
        configs: { browser: {}, twilio: {}, telnyx: {} },

        // CATALOGS
        voices: [],
        styles: [],
        models: [],
        languages: [],

        // UI COMPUTED LISTS
        availableModels: [],
        availableLanguages: [],
        availableVoices: [],
        availableStyles: [],
        availableGenders: [],
        currentGender: 'female',
        isPreviewLoading: false,

        // CAMPAIGN STATE
        campaignName: '',
        campaignFile: null,
        isCampaignLoading: false,


        // CURRENT CONFIG POINTER (Convenience accessor for UI binding)
        get c() { return this.configs[this.activeProfile]; },

        async init() {
            // 1. SAFELY PARSE SERVER DATA
            try {
                this.serverConfig = JSON.parse(document.getElementById('server-config').textContent);
                this.voices = JSON.parse(document.getElementById('server-voices').textContent);
                this.styles = JSON.parse(document.getElementById('server-styles').textContent);
                this.models = JSON.parse(document.getElementById('server-models').textContent);
                this.languages = JSON.parse(document.getElementById('server-langs').textContent);
            } catch (e) {
                console.error("CRITICAL: JSON Parsing failed", e);
                return; // Stop execution if critical data missing
            }

            // 1.1 RESTORE TAB STATE
            const urlParams = new URLSearchParams(window.location.search);
            const requestedTab = urlParams.get('tab');
            if (requestedTab) {
                this.activeTab = requestedTab.toLowerCase();
            }

            // 2. INITIALIZE CONFIG STORE FROM SERVER DATA
            this.initBrowserConfig();
            this.initTwilioConfig();
            this.initTelnyxConfig();

            // 3. SETUP WATCHERS & INITIAL UI LISTS
            this.$watch('activeProfile', () => this.refreshUI());

            // Watch provider changes AFTER init - user changing provider should update models
            this.$watch('c.provider', (newVal, oldVal) => {
                if (oldVal !== undefined && newVal !== oldVal) {
                    this.updateModelList();
                }
            });

            // Watch voiceId changes - CRITICAL for updating emotional styles visibility
            this.$watch('c.voiceId', (newVal, oldVal) => {
                if (oldVal !== undefined && newVal !== oldVal) {
                    console.log(`🎤 Voice changed: ${oldVal} → ${newVal}`);
                    this.updateStyleList();
                }
            });

            // 3.1 Initial UI Refresh
            this.refreshUI();

            // Check for helpers (Delete functionality)
            // Note: Since we moved away from partials, generic helpers might need migration or just living in the store if simple.
            // The History Checkbox helper was simple DOM manipulation. 
            // We can implement it reactively or attach to window for compatibility.
            window.toggleAllHistory = (source) => {
                // Hybrid approach for DOM elements outside Alpine scope (if any)
                // Ideally, history table should be Alpine too.
                const checkboxes = document.querySelectorAll('.history-checkbox');
                checkboxes.forEach(cb => cb.checked = source.checked);
                this.updateDeleteButton();
            };
        },

        // --- CONFIG INITIALIZERS (Refactored for brevity) ---
        initBrowserConfig() {
            const s = this.serverConfig;
            this.configs.browser = {
                provider: s.llm_provider || 'groq',
                model: s.llm_model || '',
                temp: s.temperature || 0.7,
                tokens: s.max_tokens || 250,
                msg: s.first_message || '',
                mode: s.first_message_mode || 'speak-first',
                prompt: s.system_prompt || '',

                responseLength: s.response_length || 'short',
                conversationTone: s.conversation_tone || 'warm',
                conversationFormality: s.conversation_formality || 'semi_formal',
                conversationPacing: s.conversation_pacing || 'moderate',

                // NEW: Advanced LLM Controls
                contextWindow: s.context_window || 10,
                frequencyPenalty: s.frequency_penalty || 0.0,
                presencePenalty: s.presence_penalty || 0.0,
                toolChoice: s.tool_choice || 'auto',
                dynamicVarsEnabled: s.dynamic_vars_enabled || false,
                dynamicVars: s.dynamic_vars ? JSON.stringify(s.dynamic_vars) : '',

                voiceProvider: s.tts_provider || 'azure',
                voiceLang: s.voice_language || 'es-MX',
                voiceId: s.voice_name || '',
                voiceStyle: s.voice_style || '',
                voiceSpeed: s.voice_speed || 1.0,
                voicePitch: s.voice_pitch || 0,
                voiceVolume: s.voice_volume || 100,
                voiceStyleDegree: s.voice_style_degree || 1.0,
                voicePacing: s.voice_pacing_ms || 0,
                voiceBgSound: s.background_sound || 'none',
                voiceBgUrl: s.background_sound_url || '',

                // NEW: TTS Controls (Browser)
                voiceStability: s.voice_stability || 0.5,
                voiceSimilarityBoost: s.voice_similarity_boost || 0.75,
                voiceStyleExaggeration: s.voice_style_exaggeration || 0.0,
                voiceSpeakerBoost: s.voice_speaker_boost !== undefined ? s.voice_speaker_boost : true,
                voiceMultilingual: s.voice_multilingual !== undefined ? s.voice_multilingual : true,
                ttsLatencyOptimization: s.tts_latency_optimization || 0,
                ttsOutputFormat: s.tts_output_format || 'pcm_16000',
                voiceFillerInjection: s.voice_filler_injection || false,
                voiceBackchanneling: s.voice_backchanneling || false,
                textNormalizationRule: s.text_normalization_rule || 'auto',

                sttProvider: s.stt_provider || 'azure',
                sttLang: s.stt_language || 'es-MX',
                interruptWords: s.interruption_threshold || 0,
                interruptRMSTelnyx: s.voice_sensitivity_telnyx || 3000, // Explicit Telnyx Separation
                interruptRMS: s.voice_sensitivity || 500, // Generic/Simulator
                silence: s.silence_timeout_ms || 5000,
                blacklist: s.hallucination_blacklist || '',
                enableEndCall: s.enable_end_call,
                segmentationStrategy: s.segmentation_strategy || 'default',
                enableDialKeypad: s.enable_dial_keypad,
                dialKeypad: s.enable_dial_keypad,
                transferNum: s.transfer_phone_number,
                idleTimeout: s.idle_timeout || 10,
                maxDuration: s.max_duration || 600,
                idleMessage: s.idle_message || '',
                maxRetries: s.inactivity_max_retries || 3,
                denoise: s.enable_denoising || false,
                extractionModel: s.extraction_model || 'llama-3.1-8b-instant',

                crm_enabled: s.crm_enabled || false,
                baserow_token: s.baserow_token || '',
                baserow_table_id: s.baserow_table_id || '',
                webhook_url: s.webhook_url || '',
                webhook_secret: s.webhook_secret || '',

                // ORCHESTRATION & TOOLS
                toolsSchema: s.tools_schema ? JSON.stringify(s.tools_schema) : '',
                asyncTools: s.tools_async || false,
                clientToolsEnabled: s.client_tools_enabled || false,

                toolServerUrl: s.tool_server_url || '',
                toolServerSecret: s.tool_server_secret || '',
                toolTimeoutMs: s.tool_timeout_ms || 5000,
                toolRetryCount: s.tool_retry_count || 0,
                toolErrorMsg: s.tool_error_msg || '',

                redactParams: s.redact_params ? JSON.stringify(s.redact_params) : '',
                transferWhitelist: s.transfer_whitelist ? JSON.stringify(s.transfer_whitelist) : '',
                stateInjectionEnabled: s.state_injection_enabled !== undefined ? s.state_injection_enabled : true,

                // Global Rate Limits (Advanced)
                rateLimitGlobal: s.rate_limit_global || 200,
                rateLimitTwilio: s.rate_limit_twilio || 30,
                rateLimitTelnyx: s.rate_limit_telnyx || 50,

                // CONNECTIVITY (Twilio)
                twilioAccountSid: s.twilio_account_sid || '',
                twilioAuthToken: s.twilio_auth_token || '',
                twilioFromNumber: s.twilio_from_number || '',

                // CONNECTIVITY (Telnyx)
                telnyxApiKey: s.telnyx_api_key || '',
                telnyxConnectionId: s.telnyx_connection_id || '',
                callerIdTelnyx: s.caller_id_telnyx || '',

                // SIP (Phone)
                sipTrunkUriPhone: s.sip_trunk_uri_phone || '',
                sipAuthUserPhone: s.sip_auth_user_phone || '',
                sipAuthPassPhone: s.sip_auth_pass_phone || '',
                fallbackNumberPhone: s.fallback_number_phone || '',
                geoRegionPhone: s.geo_region_phone || 'us-east-1',

                // SIP (Telnyx)
                sipTrunkUriTelnyx: s.sip_trunk_uri_telnyx || '',
                sipAuthUserTelnyx: s.sip_auth_user_telnyx || '',
                sipAuthPassTelnyx: s.sip_auth_pass_telnyx || '',
                fallbackNumberTelnyx: s.fallback_number_telnyx || '',
                geoRegionTelnyx: s.geo_region_telnyx || 'us-central',

                // Features
                recordingChannelsPhone: s.recording_channels_phone || 'mono',
                recordingChannelsTelnyx: s.recording_channels_telnyx || 'dual',
                hipaaEnabledPhone: s.hipaa_enabled_phone || false,
                hipaaEnabledTelnyx: s.hipaa_enabled_telnyx || false,
                dtmfListeningEnabledPhone: s.dtmf_listening_enabled_phone || false,

                // SYSTEM
                concurrencyLimit: s.concurrency_limit || 10,
                spendLimitDaily: s.spend_limit_daily || 50.0,
                environment: s.environment || 'development',
                privacyMode: s.privacy_mode || false,
                auditLogEnabled: s.audit_log_enabled || true,

                // FIXED: Added Orphaned Controls (Analysis)
                analysisPrompt: s.analysis_prompt || '',
                successRubric: s.success_rubric || '',
                sentimentAnalysis: s.sentiment_analysis || false,
                costTrackingEnabled: s.cost_tracking_enabled || false,
                extractionSchema: s.extraction_schema || '',
                piiRedactionEnabled: s.pii_redaction_enabled || false,
                logWebhookUrl: s.log_webhook_url || '',
                retentionDays: s.retention_days || 30,

                // FIXED: Orphaned Controls (Flow)
                bargeInEnabled: s.barge_in_enabled || false,
                interruptionSensitivity: s.interruption_sensitivity || 0.5,
                interruptionPhrases: s.interruption_phrases || '',
                voicemailDetectionEnabled: s.voicemail_detection_enabled || false,
                voicemailMessage: s.voicemail_message || '',
                machineDetectionSensitivity: s.machine_detection_sensitivity || 0.5,
                responseDelaySeconds: s.response_delay_seconds || 0,
                waitForGreeting: s.wait_for_greeting || false,
                hyphenationEnabled: s.hyphenation_enabled || false,
                endCallPhrases: s.end_call_phrases || '',

                // FIXED: Orphaned Controls (Transcriber) - Reasserting if missing
                sttModel: s.stt_model || 'nova-2',
                sttKeywords: s.stt_keywords || '',
                sttPunctuation: s.stt_punctuation || true,
                sttSmartFormatting: s.stt_smart_formatting || true,
                sttProfanityFilter: s.stt_profanity_filter || false,
                sttDiarization: s.stt_diarization || false,
                sttMultilingual: s.stt_multilingual || false,

                // FIXED: Connectivity (Specifics)
                recordingEnabledPhone: s.recording_enabled_phone || false,
                enableRecordingTelnyx: s.enable_recording_telnyx || false,
                dtmfListeningEnabledTelnyx: s.dtmf_listening_enabled_telnyx || false
            };
        },

        initTwilioConfig() {
            const s = this.serverConfig;
            this.configs.twilio = {
                provider: s.llm_provider_phone || s.llm_provider || 'groq',
                model: s.llm_model_phone || s.llm_model || '',
                temp: s.temperature_phone || s.temperature || 0.7,
                tokens: s.max_tokens_phone || s.max_tokens || 250,
                msg: s.first_message_phone || s.first_message || '',
                mode: s.first_message_mode_phone || s.first_message_mode || 'speak-first',
                prompt: s.system_prompt_phone || '',

                responseLength: s.response_length_phone || 'short',
                conversationTone: s.conversation_tone_phone || 'warm',
                conversationFormality: s.conversation_formality_phone || 'semi_formal',
                conversationPacing: s.conversation_pacing_phone || 'moderate',

                // NEW: Advanced LLM Controls (Phone)
                contextWindow: s.context_window_phone || 10,
                frequencyPenalty: s.frequency_penalty_phone || 0.0,
                presencePenalty: s.presence_penalty_phone || 0.0,
                toolChoice: s.tool_choice_phone || 'auto',
                dynamicVarsEnabled: s.dynamic_vars_enabled_phone || false,
                dynamicVars: s.dynamic_vars_phone ? JSON.stringify(s.dynamic_vars_phone) : '',

                voiceProvider: s.tts_provider_phone || s.tts_provider || 'azure',
                voiceLang: s.voice_language_phone || 'es-MX',
                voiceId: s.voice_name_phone || '',
                voiceStyle: s.voice_style_phone || '',
                voiceSpeed: s.voice_speed_phone || 1.0,
                voicePitch: s.voice_pitch_phone || 0,
                voiceVolume: s.voice_volume_phone || 100,
                voiceStyleDegree: s.voice_style_degree_phone || 1.0,
                voicePacing: s.voice_pacing_ms_phone || 0,
                voiceBgSound: s.background_sound_phone || 'none',

                // NEW: TTS Controls (Twilio)
                voiceStability: s.voice_stability_phone || 0.5,
                voiceSimilarityBoost: s.voice_similarity_boost_phone || 0.75,
                voiceStyleExaggeration: s.voice_style_exaggeration_phone || 0.0,
                voiceSpeakerBoost: s.voice_speaker_boost_phone !== undefined ? s.voice_speaker_boost_phone : true,
                voiceMultilingual: s.voice_multilingual_phone !== undefined ? s.voice_multilingual_phone : true,
                ttsLatencyOptimization: s.tts_latency_optimization_phone || 0,
                ttsOutputFormat: s.tts_output_format_phone || 'pcm_8000',
                voiceFillerInjection: s.voice_filler_injection_phone || false,
                voiceBackchanneling: s.voice_backchanneling_phone || false,
                textNormalizationRule: s.text_normalization_rule_phone || 'auto',

                sttProvider: s.stt_provider_phone || 'azure',
                sttLang: s.stt_language_phone || 'es-MX',
                interruptWords: s.interruption_threshold_phone || 0,
                silence: s.silence_timeout_ms_phone || 5000,
                inputMin: s.input_min_characters_phone || 0,
                blacklist: s.hallucination_blacklist_phone || '',
                denoise: s.enable_denoising_phone || false,

                crm_enabled: s.crm_enabled || false,
                baserow_token: s.baserow_token || '',
                baserow_table_id: s.baserow_table_id || '',
                webhook_url: s.webhook_url || '',
                webhook_secret: s.webhook_secret || '',

                // ORCHESTRATION & TOOLS (Phone)
                toolsSchema: s.tools_schema_phone ? JSON.stringify(s.tools_schema_phone) : '',
                asyncTools: s.tools_async_phone || false,
                clientToolsEnabled: s.client_tools_enabled_phone || false,

                toolServerUrl: s.tool_server_url_phone || '',
                toolServerSecret: s.tool_server_secret_phone || '',
                toolTimeoutMs: s.tool_timeout_ms_phone || 5000,
                toolRetryCount: s.tool_retry_count_phone || 0,
                toolErrorMsg: s.tool_error_msg_phone || '',

                redactParams: s.redact_params_phone ? JSON.stringify(s.redact_params_phone) : '',
                transferWhitelist: s.transfer_whitelist_phone ? JSON.stringify(s.transfer_whitelist_phone) : '',
                stateInjectionEnabled: s.state_injection_enabled_phone !== undefined ? s.state_injection_enabled_phone : true,

                // FIXED: Added Orphaned Controls (Analysis - Phone)
                analysisPrompt: s.analysis_prompt_phone || '',
                successRubric: s.success_rubric_phone || '',
                sentimentAnalysis: s.sentiment_analysis_phone || false,
                costTrackingEnabled: s.cost_tracking_enabled_phone || false,
                extractionSchema: s.extraction_schema_phone || '',
                piiRedactionEnabled: s.pii_redaction_enabled_phone || false,
                logWebhookUrl: s.log_webhook_url_phone || '',
                retentionDays: s.retention_days_phone || 30,

                // FIXED: Orphaned Controls (Flow - Phone)
                bargeInEnabled: s.barge_in_enabled_phone || false,
                interruptionSensitivity: s.interruption_sensitivity_phone || 0.5,
                interruptionPhrases: s.interruption_phrases_phone || '',
                voicemailDetectionEnabled: s.voicemail_detection_enabled_phone || false,
                voicemailMessage: s.voicemail_message_phone || '',
                machineDetectionSensitivity: s.machine_detection_sensitivity_phone || 0.5,
                responseDelaySeconds: s.response_delay_seconds_phone || 0,
                waitForGreeting: s.wait_for_greeting_phone || false,
                hyphenationEnabled: s.hyphenation_enabled_phone || false,
                endCallPhrases: s.end_call_phrases_phone || '',

                // FIXED: Orphaned Controls (Transcriber - Phone)
                sttModel: s.stt_model_phone || 'nova-2',
                sttKeywords: s.stt_keywords_phone || '',
                sttPunctuation: s.stt_punctuation_phone || true,
                sttSmartFormatting: s.stt_smart_formatting_phone || true,
                sttProfanityFilter: s.stt_profanity_filter_phone || false,
                sttDiarization: s.stt_diarization_phone || false,
                sttMultilingual: s.stt_multilingual_phone || false,

                // FIXED: Connectivity specifics
                recordingEnabledPhone: s.recording_enabled_phone || false
            };
        },

        initTelnyxConfig() {
            const s = this.serverConfig;
            this.configs.telnyx = {
                provider: s.llm_provider_telnyx || s.llm_provider || 'groq',
                model: s.llm_model_telnyx || s.llm_model || '',
                temp: s.temperature_telnyx || s.temperature || 0.7,
                tokens: s.max_tokens_telnyx || s.max_tokens || 250,
                msg: s.first_message_telnyx || s.first_message || '',
                mode: s.first_message_mode_telnyx || s.first_message_mode || 'speak-first',
                prompt: s.system_prompt_telnyx || '',

                responseLength: s.response_length_telnyx || 'short',
                conversationTone: s.conversation_tone_telnyx || 'warm',
                conversationFormality: s.conversation_formality_telnyx || 'semi_formal',
                conversationPacing: s.conversation_pacing_telnyx || 'moderate',

                // NEW: Advanced LLM Controls (Telnyx)
                contextWindow: s.context_window_telnyx || 10,
                frequencyPenalty: s.frequency_penalty_telnyx || 0.0,
                presencePenalty: s.presence_penalty_telnyx || 0.0,
                toolChoice: s.tool_choice_telnyx || 'auto',
                dynamicVarsEnabled: s.dynamic_vars_enabled_telnyx || false,
                dynamicVars: s.dynamic_vars_telnyx ? JSON.stringify(s.dynamic_vars_telnyx) : '',

                voiceProvider: s.tts_provider_telnyx || s.tts_provider || 'azure',
                voiceLang: s.voice_language_telnyx || 'es-MX',
                voiceId: s.voice_name_telnyx || '',
                voiceStyle: s.voice_style_telnyx || '',
                voiceSpeed: s.voice_speed_telnyx || 1.0,
                voicePitch: s.voice_pitch_telnyx || 0,
                voiceVolume: s.voice_volume_telnyx || 100,
                voiceStyleDegree: s.voice_style_degree_telnyx || 1.0,
                voicePacing: s.voice_pacing_ms_telnyx || 0,
                voiceBgSound: s.background_sound_telnyx || 'none',
                voiceBgUrl: s.background_sound_url_telnyx || '',

                // NEW: TTS Controls (Telnyx)
                voiceStability: s.voice_stability_telnyx || 0.5,
                voiceSimilarityBoost: s.voice_similarity_boost_telnyx || 0.75,
                voiceStyleExaggeration: s.voice_style_exaggeration_telnyx || 0.0,
                voiceSpeakerBoost: s.voice_speaker_boost_telnyx !== undefined ? s.voice_speaker_boost_telnyx : true,
                voiceMultilingual: s.voice_multilingual_telnyx !== undefined ? s.voice_multilingual_telnyx : true,
                ttsLatencyOptimization: s.tts_latency_optimization_telnyx || 0,
                ttsOutputFormat: s.tts_output_format_telnyx || 'pcm_8000',
                voiceFillerInjection: s.voice_filler_injection_telnyx || false,
                voiceBackchanneling: s.voice_backchanneling_telnyx || false,
                textNormalizationRule: s.text_normalization_rule_telnyx || 'auto',

                sttProvider: s.stt_provider_telnyx || 'azure',
                sttLang: s.stt_language_telnyx || 'es-MX',
                interruptWords: s.interruption_threshold_telnyx || 0,
                interruptRMS: s.voice_sensitivity_telnyx || 0,
                silence: s.silence_timeout_ms_telnyx || 5000,
                inputMin: s.input_min_characters_telnyx || 0,
                blacklist: s.hallucination_blacklist_telnyx || '',
                denoise: s.enable_denoising_telnyx || false,
                krisp: s.enable_krisp_telnyx || false,
                vad: s.enable_vad_telnyx || false,
                vad_threshold: s.vad_threshold_telnyx || 0.5,

                // Calculated UI Props
                time_patience: (s.silence_timeout_ms_telnyx || 5000) / 1000,

                idleTimeout: s.idle_timeout_telnyx || 20,
                maxDuration: s.max_duration_telnyx || 600,

                // Advanced Audio (Telnyx)
                audioCodec: s.audio_codec_telnyx || 'PCMU',
                noiseSuppressionLevel: s.noise_suppression_level_telnyx || 'balanced',
                enableBackchannel: s.enable_backchannel_telnyx || false,
                idleMessage: s.idle_message_telnyx || '',
                enableRecording: s.enable_recording_telnyx || false,
                amdConfig: s.amd_config_telnyx || 'disabled',

                crmEnabled: s.crm_enabled_telnyx !== undefined ? s.crm_enabled_telnyx : (s.crm_enabled || false),
                baserowToken: s.baserow_token_telnyx || s.baserow_token || '',
                baserowTableId: s.baserow_table_id_telnyx || s.baserow_table_id || '',
                webhookUrl: s.webhook_url_telnyx || s.webhook_url || '',
                webhookSecret: s.webhook_secret_telnyx || s.webhook_secret || '',

                // ORCHESTRATION & TOOLS (Telnyx)
                toolsSchema: s.tools_schema_telnyx ? JSON.stringify(s.tools_schema_telnyx) : '',
                asyncTools: s.tools_async_telnyx || false,
                clientToolsEnabled: s.client_tools_enabled_telnyx || false,

                toolServerUrl: s.tool_server_url_telnyx || '',
                toolServerSecret: s.tool_server_secret_telnyx || '',
                toolTimeoutMs: s.tool_timeout_ms_telnyx || 5000,
                toolRetryCount: s.tool_retry_count_telnyx || 0,
                toolErrorMsg: s.tool_error_msg_telnyx || '',

                redactParams: s.redact_params_telnyx ? JSON.stringify(s.redact_params_telnyx) : '',
                transferWhitelist: s.transfer_whitelist_telnyx ? JSON.stringify(s.transfer_whitelist_telnyx) : '',
                stateInjectionEnabled: s.state_injection_enabled_telnyx !== undefined ? s.state_injection_enabled_telnyx : true,

                // SYSTEM & SAFETY (Telnyx)
                maxRetries: s.max_retries_telnyx || 3,
                concurrencyLimit: s.concurrency_limit_telnyx || 10,
                spendLimitDaily: s.daily_spend_limit_telnyx || 50.00,
                environment: s.environment_tag_telnyx || 'development',
                privacyMode: s.privacy_mode_telnyx || false,
                auditLogEnabled: s.audit_log_enabled_telnyx || false,

                // CONNECTIVITY & SIP
                telnyxConnectionId: s.telnyx_connection_id || '',
                telnyxApiKey: s.telnyx_api_key || '', // Usually hidden/env
                sipTrunkUriTelnyx: s.sip_trunk_uri_telnyx || '',
                sipAuthUserTelnyx: s.sip_auth_user_telnyx || '',
                sipAuthPassTelnyx: s.sip_auth_pass_telnyx || '',
                callerIdTelnyx: s.caller_id_telnyx || '',
                fallbackNumberTelnyx: s.fallback_number_telnyx || '',
                geoRegionTelnyx: s.geo_region_telnyx || 'us-central',

                // FLOW
                endCallPhrases: s.end_call_phrases_telnyx ? JSON.stringify(s.end_call_phrases_telnyx) : '',
                transferPhoneNumber: s.transfer_phone_number_telnyx || '',

                // FIXED: Added Orphaned Controls (Analysis - Telnyx)
                analysisPrompt: s.analysis_prompt_telnyx || '',
                successRubric: s.success_rubric_telnyx || '',
                sentimentAnalysis: s.sentiment_analysis_telnyx || false,
                costTrackingEnabled: s.cost_tracking_enabled_telnyx || false,
                extractionSchema: s.extraction_schema_telnyx || '',
                piiRedactionEnabled: s.pii_redaction_enabled_telnyx || false,
                logWebhookUrl: s.log_webhook_url_telnyx || '',
                retentionDays: s.retention_days_telnyx || 30,

                // FIXED: Orphaned Controls (Flow - Telnyx)
                bargeInEnabled: s.barge_in_enabled_telnyx || false,
                interruptionSensitivity: s.interruption_sensitivity_telnyx || 0.5,
                interruptionPhrases: s.interruption_phrases_telnyx || '',
                voicemailDetectionEnabled: s.voicemail_detection_enabled_telnyx || false,
                voicemailMessage: s.voicemail_message_telnyx || '',
                machineDetectionSensitivity: s.machine_detection_sensitivity_telnyx || 0.5,
                responseDelaySeconds: s.response_delay_seconds_telnyx || 0,
                waitForGreeting: s.wait_for_greeting_telnyx || false,
                hyphenationEnabled: s.hyphenation_enabled_telnyx || false,
                // endCallPhrases handled above

                // FIXED: Orphaned Controls (Transcriber - Telnyx)
                sttModel: s.stt_model_telnyx || 'nova-2',
                sttKeywords: s.stt_keywords_telnyx || '',
                sttPunctuation: s.stt_punctuation_telnyx || true,
                sttSmartFormatting: s.stt_smart_formatting_telnyx || true,
                sttProfanityFilter: s.stt_profanity_filter_telnyx || false,
                sttDiarization: s.stt_diarization_telnyx || false,
                sttMultilingual: s.stt_multilingual_telnyx || false,

                // FIXED: Connectivity specifics
                enableRecordingTelnyx: s.enable_recording_telnyx || false,
                dtmfListeningEnabledTelnyx: s.dtmf_listening_enabled_telnyx || false
            };
        },

        ensureModelExists(provider, modelId) {
            if (!provider || !modelId) return;
            const p = provider.trim().toLowerCase();
            const m = modelId.trim();
            if (!this.models[p]) this.models[p] = [];
            const exists = this.models[p].find(x => x.id === m);
            if (!exists) {
                this.models[p].unshift({ id: m, name: m + ' (Saved)' });
            }
        },

        sanitizeAllProfiles() {
            const s = this.serverConfig || {};
            this.ensureModelExists(s.llm_provider, s.llm_model);
            this.ensureModelExists(s.llm_provider_phone, s.llm_model_phone);
            this.ensureModelExists(s.llm_provider_telnyx, s.llm_model_telnyx);
        },

        refreshUI() {
            this.sanitizeAllProfiles();
            this.updateModelList();
            this.updateVoiceLists();
        },

        updateModelList() {
            const currentProvider = (this.c.provider || 'groq').trim().toLowerCase();
            this.availableModels = this.models[currentProvider] || [];

            const s = this.serverConfig || {};
            let savedModel = '';
            if (this.activeProfile === 'browser') savedModel = s.llm_model;
            else if (this.activeProfile === 'twilio') savedModel = s.llm_model_phone;
            else if (this.activeProfile === 'telnyx') savedModel = s.llm_model_telnyx;

            this.$nextTick(() => {
                const currentModelValid = this.availableModels.find(m => m.id === this.c.model);
                if (savedModel && this.availableModels.find(m => m.id === savedModel)) {
                    this.c.model = '';
                    this.$nextTick(() => { this.c.model = savedModel; });
                } else if (!currentModelValid && this.availableModels.length > 0) {
                    this.c.model = this.availableModels[0].id;
                }
            });
        },

        updateVoiceLists() {
            let prov = (this.c.voiceProvider || 'azure').trim().toLowerCase();
            this.availableLanguages = this.languages[prov] || [];
            if (!this.availableLanguages.find(l => l.id === this.c.voiceLang)) {
                this.c.voiceLang = this.availableLanguages[0]?.id || '';
            }
            let allVoices = (this.voices[prov] || {})[this.c.voiceLang] || [];
            let gendersSet = new Set(allVoices.map(v => v.gender));
            this.availableGenders = Array.from(gendersSet).map(g => ({
                id: g,
                name: g === 'female' ? 'Femenino' : (g === 'male' ? 'Masculino' : 'Neutral')
            }));
            if (!gendersSet.has(this.currentGender) && this.availableGenders.length > 0) {
                this.currentGender = this.availableGenders[0].id;
            }
            let tmpVoices = allVoices.filter(v => v.gender === this.currentGender);

            // Restore saved voice
            const s = this.serverConfig || {};
            let savedVoiceId = '';
            if (this.activeProfile === 'browser') savedVoiceId = s.voice_name;
            else if (this.activeProfile === 'twilio') savedVoiceId = s.voice_name_phone;
            else if (this.activeProfile === 'telnyx') savedVoiceId = s.voice_name_telnyx;

            this.availableVoices = tmpVoices;

            this.$nextTick(() => {
                const voiceExists = savedVoiceId && this.availableVoices.find(v => v.id === savedVoiceId);
                if (voiceExists) {
                    this.c.voiceId = '';
                    this.$nextTick(() => { this.c.voiceId = savedVoiceId; });
                } else if (this.availableVoices.length > 0) {
                    const currentValid = this.availableVoices.find(v => v.id === this.c.voiceId);
                    if (!currentValid) this.c.voiceId = this.availableVoices[0].id;
                }
            });
            this.updateStyleList();
        },

        updateStyleList(voiceIdOverride = null) {
            const vid = voiceIdOverride || this.c.voiceId;
            const rawStyles = this.styles[vid] || [];

            // Styles already come in {id, label} format from backend (with Spanish translations)
            // No transformation needed - just validate format for legacy compatibility
            this.availableStyles = rawStyles.map(s => {
                // Legacy compatibility: if somehow a string slips through, convert it
                if (typeof s === 'string') {
                    console.warn(`⚠️ Legacy string style detected: "${s}" for voice ${vid}`);
                    return { id: s, label: s.charAt(0).toUpperCase() + s.slice(1) };
                }
                return s;
            });

            // If current style doesn't exist for new voice, reset it
            if (this.c.voiceStyle && !this.availableStyles.find(s => s.id === this.c.voiceStyle)) {
                console.log(`⚠️ Style "${this.c.voiceStyle}" not available for voice ${vid}, resetting`);
                this.c.voiceStyle = '';
            }
        },

        setGender(g) {
            this.currentGender = g;
            this.updateVoiceLists();
        },

        shouldShowTab(t) {
            if (t === 'Conexión' && this.activeProfile === 'browser') return false;
            return true;
        },

        // --- ACTIONS ---
        async saveConfig() {
            console.log("💾 Attempting to save config...");
            const urlParams = new URLSearchParams(window.location.search);
            const apiKey = urlParams.get('api_key');
            const profile = this.activeProfile || 'browser';

            // DATA SOURCE: Trust the Alpine Store state, NOT the DOM inputs.
            const rawPayload = this.configs[profile];

            // VALIDATE: TTS/STT language synchronization
            if (this.c.voiceLang && this.c.sttLang && this.c.voiceLang !== this.c.sttLang) {
                const userConfirm = confirm(
                    `⚠️ ADVERTENCIA DE CONFIGURACIÓN:\n\n` +
                    `Idioma TTS (Voz): ${this.c.voiceLang}\n` +
                    `Idioma STT (Transcripción): ${this.c.sttLang}\n\n` +
                    `Los idiomas NO coinciden. Esto causará problemas:\n` +
                    `• El asistente hablará en un idioma pero entenderá otro\n` +
                    `• Ejemplo: Audio en español pero transcripción en inglés\n\n` +
                    `¿Deseas SINCRONIZAR STT con TTS automáticamente?\n` +
                    `(Si eliges "Cancelar", se guardará con idiomas diferentes)`
                );

                if (userConfirm) {
                    // Auto-sincronizar: STT toma el valor de TTS
                    this.c.sttLang = this.c.voiceLang;
                    console.log(`✅ Idiomas sincronizados: ${this.c.voiceLang}`);
                } else {
                    this.showToast('⚠️ Guardando con idiomas diferentes - verifica que esto sea intencional', 'warning');
                }
            }

            // SANITIZE: Convert JSON strings back to Objects for the API
            const payload = { ...rawPayload }; // Shallow copy

            const jsonFields = [
                'dynamicVars', 'toolsSchema', 'redactParams', 'transferWhitelist',
                'endCallPhrases', 'extractionSchema'
            ];

            for (const field of jsonFields) {
                if (typeof payload[field] === 'string') {
                    if (!payload[field].trim()) {
                        payload[field] = null;
                    } else {
                        try {
                            payload[field] = JSON.parse(payload[field]);
                        } catch (e) {
                            this.showToast(`Error JSON en ${field}: ${e.message}`, 'error');
                            return; // Stop save if invalid JSON
                        }
                    }
                }
            }

            try {
                // Use new Profile-Aware Endpoint
                const data = await api.updateProfile(profile, payload, apiKey);
                console.log("✅ Save success:", data);

                this.showToast(`Configuración Guardada (${profile.toUpperCase()})`, 'success');
                if (data.warnings && data.warnings.length > 0) {
                    setTimeout(() => this.showToast('Advertencia: ' + data.warnings.join(', '), 'error'), 500);
                }
            } catch (e) {
                console.error(e);
                this.showToast('Error al guardar: ' + e.message, 'error');
            }
        },

        async previewVoice() {
            this.isPreviewLoading = true;
            try {
                const params = {
                    voice_name: this.c.voiceId || 'es-MX-DaliaNeural',
                    voice_speed: this.c.voiceSpeed || 1.0,
                    voice_pitch: this.c.voicePitch || 0,
                    voice_volume: this.c.voiceVolume || 100,
                    voice_style: this.c.voiceStyle || '',
                    voice_style_degree: this.c.voiceStyleDegree || 1.0
                };
                const urlParams = new URLSearchParams(window.location.search);
                const blob = await api.previewVoice(params, urlParams.get('api_key'));
                const audioUrl = URL.createObjectURL(blob);
                const audio = new Audio(audioUrl);
                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    console.log('Preview playback finished');
                };
                audio.onerror = () => {
                    alert('Error al reproducir audio');
                };
                await audio.play();
            } catch (e) {
                console.error(e);
                alert('Error al generar muestra: ' + e.message);
            } finally {
                this.isPreviewLoading = false;
            }
        },

        async handleFileSelect(event) {
            const file = event.target.files[0];
            if (!file) return;
            try {
                await csvValidator.validate(file);
                this.campaignFile = file;
            } catch (err) {
                this.showToast(err, 'error');
                event.target.value = '';
                this.campaignFile = null;
            }
        },

        async uploadCampaign() {
            if (!this.campaignFile || !this.campaignName) {
                this.showToast('Faltan datos de campaña', 'error');
                return;
            }
            this.isCampaignLoading = true;
            const urlParams = new URLSearchParams(window.location.search);
            try {
                const data = await api.uploadCampaign(this.campaignName, this.campaignFile, urlParams.get('api_key'));
                this.showToast(`Campaña iniciada! Leads: ${data.leads_count}`, 'success');
                this.campaignName = '';
                this.campaignFile = null;
                // Reset input?
            } catch (e) {
                this.showToast(e.message, 'error');
            } finally {
                this.isCampaignLoading = false;
            }
        },

        // Helper Logic
        async deleteSelectedCalls() {
            if (!confirm('¿Borrar llamadas seleccionadas?')) return;

            const checkedBoxes = document.querySelectorAll('.history-checkbox:checked');
            const ids = Array.from(checkedBoxes).map(cb => parseInt(cb.value));
            const urlParams = new URLSearchParams(window.location.search);

            try {
                await api.deleteSelectedCalls(ids, urlParams.get('api_key'));
                if (window.htmx) {
                    htmx.trigger('#history-body', 'refreshHistory');
                } else {
                    window.location.reload();
                }
                // DOM Reset
                const mainToggle = document.querySelector('thead input[type="checkbox"]');
                if (mainToggle) mainToggle.checked = false;
                this.updateDeleteButton();
            } catch (e) {
                alert('Error al borrar');
            }
        },

        async showCallDetail(callId) {
            console.log("🔍 Showing detail for call:", callId);
            const modalEl = document.getElementById('callDetailModal');
            if (!modalEl) {
                console.error("Modal not found in DOM");
                return;
            }
            const modal = new bootstrap.Modal(modalEl);  // Use existing Bootstrap global

            // 1. Reset UI
            document.getElementById('detail-call-id').textContent = `#${callId}`;
            document.getElementById('detail-transcripts').innerHTML = '<div class="text-center text-slate-500 italic mt-10">Cargando...</div>';
            document.getElementById('detail-extraction-content').innerHTML = '<div class="text-slate-500 italic">Cargando datos...</div>';

            modal.show();

            try {
                // 2. Fetch Data
                const urlParams = new URLSearchParams(window.location.search);
                // Note: The backend endpoint is defined as /api/history/{id}/detail in history_router
                // But we mounted it at /api/history
                const res = await fetch(`/api/history/${callId}/detail?api_key=${urlParams.get('api_key') || ''}`);
                if (!res.ok) throw new Error("Error fetching details");

                const data = await res.json();

                // 3. Render Transcripts
                const transDiv = document.getElementById('detail-transcripts');
                if (data.transcripts.length === 0) {
                    transDiv.innerHTML = '<div class="text-center text-slate-500 italic mt-10">Sin transcripciones disponibles.</div>';
                } else {
                    transDiv.innerHTML = data.transcripts.map(t => {
                        const isUser = t.role === 'user';
                        const align = isUser ? 'items-end' : 'items-start';
                        const bg = isUser ? 'bg-slate-700 text-slate-200' : 'bg-blue-900/40 text-blue-200 border border-blue-800/50';
                        const label = isUser ? 'Usuario' : 'Asistente';
                        return `
                            <div class="flex flex-col ${align} w-full">
                                <span class="text-[10px] text-slate-500 mb-0.5 uppercase font-bold tracking-wider">${label}</span>
                                <div class="${bg} px-3 py-2 rounded-lg text-sm max-w-[90%] shadow-sm">
                                    ${t.content}
                                </div>
                            </div>
                        `;
                    }).join('');
                }

                // 4. Render Extraction
                const extDiv = document.getElementById('detail-extraction-content');
                const ext = data.call.extracted_data;

                if (!ext) {
                    extDiv.innerHTML = '<div class="p-3 rounded border border-yellow-700/50 bg-yellow-900/10 text-yellow-500 text-xs">⚠️ Sin datos extraídos.</div>';
                } else {
                    let parsed = ext;
                    if (typeof ext === 'string') {
                        try { parsed = JSON.parse(ext); } catch (e) { }
                    }

                    const entities = parsed.extracted_entities || {};

                    extDiv.innerHTML = `
                         <div class="mb-4">
                            <label class="block text-xs text-slate-500 uppercase font-bold">Resumen</label>
                            <p class="text-slate-300 text-sm leading-snug">${parsed.summary || '-'}</p>
                         </div>
                         
                         <div class="grid grid-cols-1 gap-3">
                             <div class="bg-slate-800/50 p-2 rounded border border-slate-700/50">
                                <div class="text-xs text-slate-500 uppercase">Nombre</div>
                                <div class="text-white font-medium">${entities.name || '-'}</div>
                             </div>
                             <div class="bg-slate-800/50 p-2 rounded border border-slate-700/50">
                                <div class="text-xs text-slate-500 uppercase">Teléfono</div>
                                <div class="text-white font-mono">${entities.phone || '-'}</div>
                             </div>
                             <div class="bg-slate-800/50 p-2 rounded border border-slate-700/50">
                                <div class="text-xs text-slate-500 uppercase">Intención</div>
                                <div class="text-blue-300 font-mono text-xs">${parsed.intent || '-'}</div>
                             </div>
                              <div class="bg-slate-800/50 p-2 rounded border border-slate-700/50">
                                <div class="text-xs text-slate-500 uppercase">Próxima Acción</div>
                                <div class="text-emerald-300 font-mono text-xs">${parsed.next_action || '-'}</div>
                             </div>
                         </div>
                    `;
                }

                // 5. Metadata
                document.getElementById('detail-client-type').textContent = data.call.client_type;
                document.getElementById('detail-start-time').textContent = data.call.start_time ? new Date(data.call.start_time).toLocaleString() : '-';

            } catch (err) {
                console.error(err);
                document.getElementById('detail-transcripts').innerHTML = '<div class="text-center text-red-400 mt-10">Error al cargar detalles.</div>';
            }
        },

        updateDeleteButton() {
            // This relies on DOM inspection outside typical Alpine data flow
            const checked = document.querySelectorAll('.history-checkbox:checked').length;
            const btn = document.getElementById('btn-delete-selected');
            if (btn) {
                if (checked > 0) {
                    btn.style.display = 'inline-flex';
                    btn.innerHTML = `<span>🗑️</span> Borrar (${checked})`;
                } else {
                    btn.style.display = 'none';
                }
            }
        },

        showToast(msg, type = 'info') {
            console.log(`🔔 Toast [${type}]: ${msg}`);
            const div = document.createElement('div');
            // Force styles for maximum visibility
            div.style.position = 'fixed';
            div.style.top = '20px';
            div.style.right = '20px';
            div.style.zIndex = '9999';
            div.style.padding = '12px 24px';
            div.style.borderRadius = '8px';
            div.style.color = 'white';
            div.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            div.style.backgroundColor = type === 'error' ? '#dc2626' : '#16a34a'; // Red-600 / Green-600
            div.style.fontSize = '14px';
            div.style.fontWeight = '500';
            div.style.transition = 'opacity 0.3s ease-out';

            div.innerText = msg;
            document.body.appendChild(div);

            setTimeout(() => {
                div.style.opacity = '0';
                setTimeout(() => div.remove(), 300);
            }, 3000);
        }
    };
}
