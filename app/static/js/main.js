
import { dashboardStore } from './dashboard/store.js';

// Explicitly expose dashboardStore to global window so Alpine can find it.
// In a pure Alpine build you might use Alpine.data(), but since Alpine is loaded via CDN,
// window.dashboard = ... is the bridge.
window.dashboard = dashboardStore;

console.log("🚀 [Frontend] Dashboard App Initialized (ES Module)");
