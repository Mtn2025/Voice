import { api, csvValidator } from './api.js';
import { SimulatorMixin } from './simulator.v2.js';

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

                sttProvider: s.stt_provider || 'azure',
                sttLang: s.stt_language || 'es-MX',
                interruptWords: s.interruption_threshold || 0,
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

                // Global Rate Limits (Advanced)
                rateLimitGlobal: s.rate_limit_global || 200,
                rateLimitTwilio: s.rate_limit_twilio || 30,
                rateLimitTelnyx: s.rate_limit_telnyx || 50
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
                webhook_secret: s.webhook_secret || ''
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
                idleTimeout: s.idle_timeout_telnyx || 20,
                maxDuration: s.max_duration_telnyx || 600,
                idleMessage: s.idle_message_telnyx || '',
                enableRecording: s.enable_recording_telnyx || false,
                amdConfig: s.amd_config_telnyx || 'disabled',

                crm_enabled: s.crm_enabled || false,
                baserow_token: s.baserow_token || '',
                baserow_table_id: s.baserow_table_id || '',
                webhook_url: s.webhook_url || '',
                webhook_secret: s.webhook_secret || ''
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

        updateStyleList() {
            let vid = this.c.voiceId;
            let rawStyles = this.styles[vid] || this.styles['default'] || [];
            this.availableStyles = rawStyles.map(s => {
                if (typeof s === 'string') return { id: s, label: s.charAt(0).toUpperCase() + s.slice(1) };
                return s;
            });
            if (this.c.voiceStyle && !this.availableStyles.find(s => s.id === this.c.voiceStyle)) {
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
            // Flatten config back to simple key-value for server
            const urlParams = new URLSearchParams(window.location.search);
            const apiKey = urlParams.get('api_key');

            // Create a temporary form to leverage browser's native matching with hidden inputs,
            // OR reuse the manual payload construction.
            // Since we bound all inputs in the HTML to Alpine mode, we can construct the payload from `configs`.
            // HOWEVER, the `dashboard.html` relies on hidden inputs with names.
            // We should use `new FormData(document.getElementById('configForm'))` to get everything.

            const form = document.getElementById('configForm');
            const formData = new FormData(form);
            const payload = {};
            formData.forEach((value, key) => payload[key] = value);

            try {
                const data = await api.saveConfig(payload, apiKey);
                this.showToast('Configuración Guardada', 'success');
                if (data.warnings && data.warnings.length > 0) {
                    setTimeout(() => this.showToast('Advertencia: ' + data.warnings.join(', '), 'error'), 500);
                }
            } catch (e) {
                console.error(e);
                this.showToast('Error al guardar', 'error');
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

        // Helper Logic from scripts_helpers.html
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
            const div = document.createElement('div');
            div.className = `fixed top-4 right-4 px-4 py-2 rounded shadow-lg text-white text-sm z-50 ${type === 'error' ? 'bg-red-600' : 'bg-green-600'}`;
            div.innerText = msg;
            document.body.appendChild(div);
            setTimeout(() => div.remove(), 3000);
        }
    };
}
