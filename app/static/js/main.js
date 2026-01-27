import { dashboardStore } from './dashboard/store.js';

/**
 * Registers the Alpine component safely.
 * Handles race conditions where Alpine might load before or after this module.
 */
function registerDashboard() {
    console.log("🚀 [Frontend] Registering 'dashboard' component...");
    try {
        Alpine.data('dashboard', dashboardStore);
        console.log("✅ [Frontend] Dashboard Registered Successfully");
    } catch (e) {
        console.error("❌ [Frontend] Failed to register dashboard:", e);
    }
}

// Scenario 1: Alpine is already loaded and initialized (rare with modules but possible)
if (window.Alpine) {
    registerDashboard();
}
// Scenario 2: Alpine hasn't initialized yet (Standard behavior)
else {
    document.addEventListener('alpine:init', () => {
        registerDashboard();
    });
}

// Fallback: Expose to window just in case specific directives look for global scope
// (though Alpine.data is preferred)
window.dashboard = dashboardStore;
