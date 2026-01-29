/**
 * API Client Module
 * Handles interactions with the backend (Config, Campaigns, History).
 */

export const api = {
    async saveConfig(configData, apiKey) {
        const url = apiKey
            ? `/api/config/update-json?api_key=${encodeURIComponent(apiKey)}`
            : '/api/config/update-json';

        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });

        if (!res.ok) throw new Error('Error saving config');
        return await res.json();
    },

    async updateProfile(profile, configData, apiKey) {
        // Safe profile names: browser, twilio, telnyx, core
        const p = profile.toLowerCase();
        const url = apiKey
            ? `/api/config/${p}?api_key=${encodeURIComponent(apiKey)}`
            : `/api/config/${p}`;

        const res = await fetch(url, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error updating profile');
        }
        return await res.json();
    },

    async uploadCampaign(name, file, apiKey) {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('file', file);

        const url = apiKey
            ? `/api/campaigns/start?api_key=${apiKey}`
            : '/api/campaigns/start';

        const res = await fetch(url, { method: 'POST', body: formData });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error uploading campaign');
        }
        return await res.json();
    },

    async deleteSelectedCalls(callIds, apiKey) {
        const url = `/api/history/delete-selected?api_key=${apiKey || ''}`;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ call_ids: callIds })
        });

        if (!res.ok) throw new Error('Error deleting calls');
        return true;
    },

    async previewVoice(params, apiKey) {
        const formData = new FormData();
        for (const key in params) {
            formData.append(key, params[key]);
        }
        if (apiKey) formData.append('api_key', apiKey);

        const response = await fetch('/api/voice/preview', { method: 'POST', body: formData });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Preview failed');
        }
        return await response.blob();
    }
};

export const csvValidator = {
    validate(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const text = e.target.result;
                const firstLine = text.split('\n')[0];
                const headers = firstLine.split(',').map(h => h.trim().toLowerCase());

                const hasPhone = headers.includes('phone') || headers.includes('telefono') || headers.includes('tel');
                const hasName = headers.includes('name') || headers.includes('nombre');

                if (!hasPhone || !hasName) {
                    reject('El CSV debe tener columnas "phone" y "name"');
                } else {
                    resolve(true);
                }
            };
            reader.onerror = () => reject('Error al leer archivo');
            reader.readAsText(file);
        });
    }
};
