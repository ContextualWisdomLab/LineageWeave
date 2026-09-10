import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { configDefaults } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      output: {
        // #994: split stable framework/auth vendor code out of the principal
        // application chunk so the buyer-path shell stays under the 500 kB
        // warning boundary. Vendor modules change infrequently, so a
        // content-hashed vendor chunk also improves repeat-visit caching.
        // No warning-threshold change, no source behavior change.
        manualChunks: (id) => {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/') || id.includes('node_modules/scheduler')) {
            return 'react-vendor';
          }
          if (id.includes('node_modules/oidc-client-ts') || id.includes('node_modules/react-oidc-context')) {
            return 'auth-vendor';
          }
          return undefined;
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
})
