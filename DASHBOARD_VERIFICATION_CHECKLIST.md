# Dashboard Verification Checklist

This document guides the manual verification of the Voice Orchestrator Dashboard. Use the checkbox to mark tested items.

## 1. Tab: Model
Controls for LLM configuration.

- [ ] **Provider** (`c.provider`): Select different providers (Browser/Twilio/Telnyx). Verify model list updates.
- [ ] **Model** (`c.model`): Select a model. Reload page to verify persistence.
- [ ] **Temperature** (`c.temp`): Adjust slider. Verify persistence.
- [ ] **Max Tokens** (`c.tokens`): Input valid integer. Verify persistence.
- [ ] **System Prompt** (`c.prompt`): Textarea input. Verify persistence.
- [ ] **First Message** (`c.msg`): Text input. Verify persistence.
- [ ] **Context Window** (`c.contextWindow`): Input integer. Verify persistence.
- [ ] **Frequency Penalty** (`c.frequencyPenalty`): Adjust range.
- [ ] **Presence Penalty** (`c.presencePenalty`): Adjust range.
- [ ] **Dynamic Vars** (`c.dynamicVars`): Enable checkbox and input JSON. Verify JSON validation.

## 2. Tab: Voice
Controls for TTS configuration.

- [ ] **Provider** (`c.voiceProvider`): Select provider. Verify voice list updates.
- [ ] **Language** (`c.voiceLang`): Select language. Verify voice filtering.
- [ ] **Voice ID** (`c.voiceId`): Select voice. Verify "Preview" button works.
- [ ] **Speed** (`c.voiceSpeed`): Adjust slider. Verify preview audio changes.
- [ ] **Pitch** (`c.voicePitch`): Adjust slider (if supported).
- [ ] **Background Sound** (`c.voiceBgSound`): Select ambient noise. Verify preview mixing.
- [ ] **Style** (`c.voiceStyle`): Select style (e.g., cheerful). Verify preview.
- [ ] **Speaker Boost** (`c.voiceSpeakerBoost`): Toggle checkbox.

## 3. Tab: Transcriber
Controls for STT configuration.

- [ ] **Provider** (`c.sttProvider`): Select provider (deepgram/azure).
- [ ] **Language** (`c.sttLang`): Select language.
- [ ] **Keywords** (`c.sttKeywords`): Input CSV of keywords.
- [ ] **Interruption Threshold** (`c.interruption_threshold`): Adjust slider.
- [ ] **Profanity Filter** (`c.sttProfanityFilter`): Toggle checkbox.

## 4. Tab: Connectivity
Profile-specific connectivity (Twilio/Telnyx).

### Twilio
- [ ] **From Number** (`c.twilioFromNumber`): Verify value.
- [ ] **Account SID** (`c.twilioAccountSid`): Verify value is masked/present.

### Telnyx
- [ ] **API Key** (`c.telnyxApiKey`): Verify input/masking.
- [ ] **Connection ID** (`c.telnyxConnectionId`): Verify input.
- [ ] **Recording** (`c.enableRecordingTelnyx`): Toggle checkbox.
- [ ] **Sip Trunk** (`c.sipTrunkUriTelnyx`): Verify input.

## 5. Tab: Flow
Conversation flow & event handling.

- [ ] **Silence Timeout** (`c.silence_timeout_ms`): Adjust slider.
- [ ] **Response Delay** (`c.responseDelaySeconds`): Adjust slider.
- [ ] **Barge In** (`c.bargeInEnabled`): Toggle checkbox. Verify user can interrupt agent.
- [ ] **Voicemail Detection** (`c.voicemailDetectionEnabled`): Toggle checkbox.
- [ ] **End Call Phrases** (`c.endCallPhrases`): Input JSON list.

## 6. Tab: Tools
Function calling and external tools.

- [ ] **Client Tools** (`c.clientToolsEnabled`): Toggle checkbox.
- [ ] **Async Tools** (`c.asyncTools`): Toggle checkbox.
- [ ] **Tool Timeout** (`c.toolTimeoutMs`): Input integer.
- [ ] **Schema Definition** (`c.toolsSchema`): Input JSON schema.

## 7. Tab: Analysis
Post-call analysis and webhooks.

- [ ] **Analysis Prompt** (`c.analysisPrompt`): Textarea input.
- [ ] **Sentiment Analysis** (`c.sentimentAnalysis`): Toggle checkbox.
- [ ] **Webhook URL** (`c.webhookUrl`): Input URL. Verify test ping.

## 8. Tab: System
Global system settings.

- [ ] **Concurrency Limit** (`c.concurrencyLimit`): Adjust range.
- [ ] **Audit Log** (`c.auditLogEnabled`): Toggle checkbox.
- [ ] **Environment** (`c.environment`): Select dev/prod.

## 9. Tab: Campaigns
Outbound campaign management.

- [ ] **Campaign Name**: Input text.
- [ ] **CSV Upload**: Upload valid CSV. Verify validation success.
- [ ] **Start Campaign**: Click button. Verify simulated calls initiate.

## Integration Tests
- [ ] **Save Config**: Click "Guardar Configuración". Verify Toast success message.
- [ ] **Profile Switch**: Switch between Browser/Twilio/Telnyx. Verify settings reload relevant profile values.
- [ ] **Simulation**: Start simulation in "Browser" profile. Speak to agent. Verify TTS matches Voice tab settings.
