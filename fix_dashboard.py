import os

path = r'c:\Users\Martin\Desktop\Asistente Andrea\app\templates\dashboard.html'
try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading file: {e}")
    exit(1)

# Global fix for spaces in Jinja delimiters
content = content.replace('{ {', '{{').replace('} }', '}}')

# Define the start and end markers for the configs block
# Use unique surrounding comments
start_marker = "// --- DATA STORES (From Backend) ---"
end_marker = "// --- UI BOUND VARIABLES ---"

if start_marker not in content or end_marker not in content:
    print("Error: Markers not found")
    exit(1)

pre_block, temp = content.split(start_marker)
# split on the *first* occurrence of end_marker after start_marker
# tricky if end_marker appears multiple times? It shouldn't.
middle, post_block = temp.split(end_marker)

# The 'middle' contains the broken configs object.
# We will replace 'middle' with our fixed valid object.
# Note: middle starts with whatever was after start_marker (newlines) and ends before end_marker.

# Fixed configs block
fixed_configs = """
                                    configs: {
                                        browser: {
                                            provider: {{ (config.llm_provider or 'openai') | tojson }},
                                            model: {{ (config.llm_model or 'gpt-3.5-turbo') | tojson }},
                                            temp: {{ config.temperature or 0.7 }},
                                            tokens: {{ config.max_tokens or 250 }},
                                            msg: {{ (config.first_message or '') | tojson }},
                                            mode: {{ (config.first_message_mode or 'speak-first') | tojson }},
                                            prompt: {{ (config.system_prompt or '') | tojson }},

                                            /* VOICE CONFIG */
                                            voiceProvider: {{ (config.tts_provider or 'azure') | tojson }},
                                            voiceLang: {{ (config.voice_language or "es-MX") | tojson }},
                                            voiceId: {{ (config.voice_name or '') | tojson }},
                                            voiceStyle: {{ (config.voice_style or '') | tojson }},
                                            voiceSpeed: {{ config.voice_speed or 1.0 }},
                                            voicePacing: {{ config.voice_pacing_ms or 0 }},
                                            voiceBgSound: {{ (config.background_sound or 'none') | tojson }},
                                            voiceBgUrl: {{ (config.background_sound_url or '') | tojson }},

                                            /* FUNCTIONS */
                                            enableEndCall: {{ 'true' if config.enable_end_call else 'false' }},
                                            dialKeypad: {{ 'true' if config.enable_dial_keypad else 'false' }},
                                            transferNum: {{ (config.transfer_phone_number or "") | tojson }},

                                            /* ADVANCED */
                                            idleTimeout: {{ config.idle_timeout or 10 }},
                                            maxDuration: {{ config.max_duration or 600 }},
                                            idleMessage: {{ (config.idle_message or '') | tojson }},
                                            maxRetries: {{ config.inactivity_max_retries or 3 }},

                                            /* TRANSCRIBER CONFIG */
                                            sttProvider: {{ (config.stt_provider or 'azure') | tojson }},
                                            sttLang: {{ (config.stt_language or 'es-MX') | tojson }},
                                            interruptWords: {{ config.interruption_threshold or 0 }},
                                            silence: {{ config.silence_timeout_ms or 5000 }},
                                            inputMin: 0,
                                            blacklist: {{ (config.hallucination_blacklist or '') | tojson }},
                                            denoise: false,
                                            krisp: false,
                                            vad: false
                                        },
                                        twilio: {
                                            provider: {{ (config.llm_provider_phone or config.llm_provider or 'openai') | tojson }},
                                            model: {{ (config.llm_model_phone or config.llm_model or 'gpt-3.5-turbo') | tojson }},
                                            temp: {{ config.temperature_phone or config.temperature or 0.7 }},
                                            tokens: {{ config.max_tokens_phone or config.max_tokens or 250 }},
                                            msg: {{ (config.first_message_phone or config.first_message or '') | tojson }},
                                            mode: {{ (config.first_message_mode_phone or config.first_message_mode or 'speak-first') | tojson }},
                                            prompt: {{ (config.system_prompt_phone or '') | tojson }},

                                            /* VOICE CONFIG PHONE */
                                            voiceProvider: {{ (config.tts_provider_phone or config.tts_provider or 'azure') | tojson }},
                                            voiceLang: {{ (config.voice_language_phone or "es-MX") | tojson }},
                                            voiceId: {{ (config.voice_name_phone or '') | tojson }},
                                            voiceStyle: {{ (config.voice_style_phone or '') | tojson }},
                                            voiceSpeed: {{ config.voice_speed_phone or 1.0 }},
                                            voicePacing: {{ config.voice_pacing_ms_phone or 0 }},
                                            voiceBgSound: {{ (config.background_sound_phone or 'none') | tojson }},
                                            voiceBgUrl: {{ (config.background_sound_url_phone or '') | tojson }},

                                            /* FUNCTIONS PHONE */
                                            enableEndCall: {{ 'true' if config.enable_end_call else 'false' }},
                                            dialKeypad: {{ 'true' if config.enable_dial_keypad else 'false' }},
                                            transferNum: {{ (config.transfer_phone_number or "") | tojson }},

                                            /* ADVANCED PHONE (Legacy/Shared) */
                                            idleTimeout: {{ config.idle_timeout or 10 }},
                                            maxDuration: {{ config.max_duration or 600 }},
                                            idleMessage: {{ (config.idle_message_phone or '') | tojson }},
                                            maxRetries: {{ config.inactivity_max_retries or 3 }},

                                            /* TRANSCRIBER CONFIG PHONE */
                                            sttProvider: {{ (config.stt_provider_phone or 'azure') | tojson }},
                                            sttLang: {{ (config.stt_language_phone or 'es-MX') | tojson }},
                                            interruptWords: {{ config.interruption_threshold_phone or 0 }},
                                            silence: {{ config.silence_timeout_ms_phone or 5000 }},
                                            inputMin: {{ config.input_min_characters_phone or 0 }},
                                            blacklist: {{ (config.hallucination_blacklist_phone or '') | tojson }},
                                            denoise: {{ 'true' if config.enable_denoising_phone else 'false' }},
                                            krisp: false,
                                            vad: false
                                        },
                                        telnyx: {
                                            provider: {{ (config.llm_provider_telnyx or config.llm_provider or 'openai') | tojson }},
                                            model: {{ (config.llm_model_telnyx or config.llm_model or 'gpt-3.5-turbo') | tojson }},
                                            temp: {{ config.temperature_telnyx or config.temperature or 0.7 }},
                                            tokens: {{ config.max_tokens_telnyx or config.max_tokens or 250 }},
                                            msg: {{ (config.first_message_telnyx or config.first_message or '') | tojson }},
                                            mode: {{ (config.first_message_mode_telnyx or config.first_message_mode or 'speak-first') | tojson }},
                                            prompt: {{ (config.system_prompt_telnyx or '') | tojson }},

                                            /* VOICE CONFIG TELNYX */
                                            voiceProvider: {{ (config.tts_provider_telnyx or config.tts_provider or 'azure') | tojson }},
                                            voiceLang: {{ (config.voice_language_telnyx or "es-MX") | tojson }},
                                            voiceId: {{ (config.voice_name_telnyx or '') | tojson }},
                                            voiceStyle: {{ (config.voice_style_telnyx or '') | tojson }},
                                            voiceSpeed: {{ config.voice_speed_telnyx or 1.0 }},
                                            voicePacing: {{ config.voice_pacing_ms_telnyx or 0 }},
                                            voiceBgSound: {{ (config.background_sound_telnyx or 'none') | tojson }},
                                            voiceBgUrl: {{ (config.background_sound_url_telnyx or '') | tojson }},

                                            /* FUNCTIONS TELNYX */
                                            enableEndCall: {{ 'true' if config.enable_end_call else 'false' }},
                                            dialKeypad: {{ 'true' if config.enable_dial_keypad else 'false' }},
                                            transferNum: {{ (config.transfer_phone_number or "") | tojson }},

                                            /* ADVANCED TELNYX */
                                            idleTimeout: {{ config.idle_timeout_telnyx or 20 }},
                                            maxDuration: {{ config.max_duration_telnyx or 600 }},
                                            idleMessage: {{ (config.idle_message_telnyx or '') | tojson }},
                                            enableRecording: {{ 'true' if config.enable_recording_telnyx else 'false' }},
                                            amdConfig: {{ (config.amd_config_telnyx or "disabled") | tojson }},

                                            /* TRANSCRIBER CONFIG TELNYX */
                                            sttProvider: {{ (config.stt_provider_telnyx or 'azure') | tojson }},
                                            sttLang: {{ (config.stt_language_telnyx or 'es-MX') | tojson }},
                                            interruptWords: {{ config.interruption_threshold_telnyx or 0 }},
                                            interruptRMS: {{ config.voice_sensitivity_telnyx or 0 }},
                                            silence: {{ config.silence_timeout_ms_telnyx or 5000 }},
                                            inputMin: {{ config.input_min_characters_telnyx or 0 }},
                                            blacklist: {{ (config.hallucination_blacklist_telnyx or '') | tojson }},
                                            denoise: {{ 'true' if config.enable_denoising_telnyx else 'false' }},
                                            krisp: {{ 'true' if config.enable_krisp_telnyx else 'false' }},
                                            vad: {{ 'true' if config.enable_vad_telnyx else 'false' }}
                                        },
                                    },

"""

# Reconstruct
# preserve newlines around markers
new_content = pre_block + start_marker + "\\n" + fixed_configs + "\\n                            " + end_marker + post_block

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
