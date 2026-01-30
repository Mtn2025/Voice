import Alpine from 'https://unpkg.com/alpinejs@3.13.3/dist/module.esm.js';
import collapse from 'https://unpkg.com/@alpinejs/collapse@3.13.3/dist/module.esm.js';

Alpine.plugin(collapse);

import { dashboardStore } from './dashboard/store.v2.js?v=ui_fix_1';

console.log("🚀 [Frontend] Initializing App...");

// 1. Register Data Components
import CustomSelect from './components/custom-select.js';

Alpine.data('dashboard', dashboardStore);
Alpine.data('customSelect', CustomSelect);

// 2. Expose Alpine to window for debugging (optional)
window.Alpine = Alpine;

// 3. Start Alpine
// This scans the DOM and initializes components.
// Since we are running this inside a module, the DOM is likely ready,
// but we check just in case.
Alpine.start();

console.log("✅ [Frontend] AlpineJS Started & Dashboard Registered");
