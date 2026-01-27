import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
    build: {
        // Write output to app/static/css for easy serving by FastAPI
        outDir: 'app/static/css',
        emptyOutDir: false, // Don't delete other static files
        rollupOptions: {
            input: resolve(__dirname, 'app/static/css/input.css'),
            output: {
                // Force the output filename to be consistent (no hash) for easier linking in templates
                assetFileNames: 'output.css',
            }
        }
    },
    // Suppress clear screen in non-interactive environments
    clearScreen: false,
});
