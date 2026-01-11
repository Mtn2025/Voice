// DEBUG SCRIPT - Paste this in browser console to see what's happening

// 1. Check serverConfig
const serverConfigElement = document.getElementById('server-config');
if (serverConfigElement) {
    const config = JSON.parse(serverConfigElement.textContent);
    console.log('=== SERVER CONFIG ===');
    console.log('llm_provider:', config.llm_provider);
    console.log('llm_model:', config.llm_model);
    console.log('llm_provider_phone:', config.llm_provider_phone);
    console.log('llm_model_phone:', config.llm_model_phone);
    console.log('llm_provider_telnyx:', config.llm_provider_telnyx);
    console.log('llm_model_telnyx:', config.llm_model_telnyx);
} else {
    console.error('server-config element not found');
}

// 2. Check Alpine.js state
setTimeout(() => {
    const alpineData = Alpine.$data(document.querySelector('[x-data]'));
    if (alpineData) {
        console.log('=== ALPINE DATA ===');
        console.log('activeProfile:', alpineData.activeProfile);
        console.log('configs.browser.provider:', alpineData.configs.browser.provider);
        console.log('configs.browser.model:', alpineData.configs.browser.model);
        console.log('configs.twilio.provider:', alpineData.configs.twilio?.provider);
        console.log('configs.twilio.model:', alpineData.configs.twilio?.model);
    }
}, 1000);
