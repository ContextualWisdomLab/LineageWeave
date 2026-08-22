/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    // e2e/ runs under Playwright (npx playwright test), against a live
    // authenticated stack -- vitest's default include pattern would
    // otherwise also try to run those specs under jsdom.
    exclude: ['**/node_modules/**', 'e2e/**'],
  },
})
